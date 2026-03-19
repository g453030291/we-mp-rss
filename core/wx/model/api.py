import json
import requests
import time
import random
import yaml
import re
from bs4 import BeautifulSoup
from core.config import cfg
from core.wx.base import WxGather
from core.print import print_error, print_info, print_warning
from core.log import logger
# 继承 BaseGather 类
class MpsApi(WxGather):
    def _should_reuse_browser(self) -> bool:
        return bool(cfg.get("gather.reuse_browser_per_feed", False))

    # 重写 content_extract 方法
    def fetch_content(self, url, fetcher=None, keep_browser=False):
        try:
            text = super().content_extract(url)
            if text:
                return text, "api"
        except Exception as e:
            logger.error(e)

        if not cfg.get("gather.api_content_fallback_web", True):
            return "", "api"

        try:
            from driver.wxarticle import Web as DefaultFetcher
            app = fetcher or DefaultFetcher
            print_warning(f"[api][content] api empty, fallback to web: {url}")
            r = app.get_article_content(url, keep_browser=keep_browser)
            if r is not None:
                text = r.get("content","")
                text=self.remove_common_html_elements(text)
                if text:
                    return text, "web"
        except Exception as e:
            logger.error(e)
        return "", "api"

    def _fetch_api_list(self, session, faker_id, begin, count):
        url = "https://mp.weixin.qq.com/cgi-bin/appmsg"
        params = {
            "action": "list_ex",
            "begin": str(begin),
            "count": count,
            "fakeid": faker_id,
            "type": "9",
            "token": self.token,
            "lang": "zh_CN",
            "f": "json",
            "ajax": "1"
        }
        headers = self.fix_header(url)
        resp = session.get(url, headers=headers, params=params, verify=False)
        return resp.json(), resp.cookies, "appmsg"

    def _fetch_publish_list(self, session, faker_id, begin, count):
        url = "https://mp.weixin.qq.com/cgi-bin/appmsgpublish"
        params = {
            "sub": "list",
            "sub_action": "list_ex",
            "begin": str(begin),
            "count": count,
            "fakeid": faker_id,
            "token": self.token,
            "lang": "zh_CN",
            "f": "json",
            "ajax": 1
        }
        headers = self.fix_header(url)
        resp = session.get(url, headers=headers, params=params, verify=False)
        return resp.json(), resp.cookies, "publish"

    def _extract_publish_items(self, msg: dict):
        publish_page = msg.get("publish_page")
        if not publish_page:
            return []
        if isinstance(publish_page, str):
            publish_page = json.loads(publish_page)

        items = []
        for publish_item in publish_page.get("publish_list", []):
            publish_info = publish_item.get("publish_info")
            if not publish_info:
                continue
            publish_info = json.loads(publish_info)
            items.extend(publish_info.get("appmsgex", []))
        return items
    # 重写 get_Articles 方法
    def get_Articles(self, faker_id:str=None,Mps_id:str=None,Mps_title="",CallBack=None,start_page=0,MaxPage:int=1,interval=10,Gather_Content=True,Item_Over_CallBack=None,Over_CallBack=None):
        super().Start(mp_id=Mps_id)
        if self.Gather_Content:
             Gather_Content=True
        print(f"API获取模式,是否采集[{Mps_title}]内容：{Gather_Content}\n")
        count=5

        # 连接超时
        session=self.session
        fallback_fetcher = None
        stop_on_first_duplicate = cfg.get("gather.stop_on_first_duplicate", True)
        stats = {
            "pages": 0,
            "items": 0,
            "inserted": 0,
            "skipped_existing": 0,
            "list_fallback_pages": 0,
            "content_web_fallback": 0,
        }
        stop_feed = False
        reuse_browser = self._should_reuse_browser()
        if Gather_Content and cfg.get("gather.api_content_fallback_web", True) and reuse_browser:
            from driver.wxarticle import WXArticleFetcher
            fallback_fetcher = WXArticleFetcher()
        # 起始页数
        i = start_page
        try:
            while True:
                if i >= MaxPage or stop_feed:
                    break
                begin = i * count
                print(f"第{i+1}页开始爬取\n")
                # 随机暂停几秒，避免过快的请求导致过快的被查到
                time.sleep(random.randint(0,interval))
                try:
                    msg, cookies, list_source = self._fetch_api_list(session, faker_id, begin, count)
                    self._cookies=cookies
                    ret = msg.get("base_resp", {}).get("ret")

                    if ret == 200013 and cfg.get("gather.api_list_fallback_publish", True):
                        print_warning(f"[api][list] appmsg limited, fallback to publish, begin={begin}")
                        msg, cookies, list_source = self._fetch_publish_list(session, faker_id, begin, count)
                        self._cookies = cookies
                        stats["list_fallback_pages"] += 1
                        ret = msg.get("base_resp", {}).get("ret")

                    # 流量控制了, 退出
                    if ret == 200013:
                        super().Error("frequencey control, stop at {}".format(str(begin)))
                        break
                    
                    if ret == 200003:
                        super().Error("Invalid Session, stop at {}".format(str(begin)),code="Invalid Session")
                        break

                    if ret != 0:
                        super().Error(
                            "错误原因:{}:代码:{}".format(
                                msg['base_resp']['err_msg'],
                                msg['base_resp']['ret']
                            ),
                            code=msg['base_resp']['err_msg']
                        )
                        break

                    if list_source == "appmsg":
                        items = msg.get("app_msg_list", [])
                        if not items and cfg.get("gather.api_list_fallback_publish", True):
                            print_warning(f"[api][list] appmsg empty, fallback to publish, begin={begin}")
                            msg, cookies, list_source = self._fetch_publish_list(session, faker_id, begin, count)
                            self._cookies = cookies
                            stats["list_fallback_pages"] += 1
                            ret = msg.get("base_resp", {}).get("ret")
                            if ret != 0:
                                super().Error(
                                    "错误原因:{}:代码:{}".format(
                                        msg['base_resp']['err_msg'],
                                        msg['base_resp']['ret']
                                    ),
                                    code=msg['base_resp']['err_msg']
                                )
                                break
                            items = self._extract_publish_items(msg)
                    else:
                        items = self._extract_publish_items(msg)

                    # 如果返回的内容中为空则结束
                    if not items:
                        super().Error("all ariticle parsed")
                        break

                    stats["pages"] += 1
                    stats["items"] += len(items)
                    print_info(f"[api][list] source={list_source} page={i+1} items={len(items)}")
                    for item in items:
                        aid = item.get("aid", "")
                        title = item.get("title", "")
                        link = item.get("link", "")
                        if aid and super().HasGathered(aid):
                            continue
                        item["id"] = aid
                        item["mp_id"] = Mps_id

                        if super().article_exists(article_id=item["id"], mp_id=Mps_id, url=link):
                            stats["skipped_existing"] += 1
                            print_info(f"[api][article] skip existing: {title}")
                            if stop_on_first_duplicate:
                                stop_feed = True
                                print_warning(f"[api][feed] stop on existing article: {title}")
                                break
                            continue

                        time.sleep(random.randint(1,2))
                        if Gather_Content:
                            item["content"], content_source = self.fetch_content(
                                link,
                                fetcher=fallback_fetcher,
                                keep_browser=reuse_browser,
                            )
                            if content_source == "web":
                                stats["content_web_fallback"] += 1
                            super().Wait(1,3,tips=f"{item['title']} 采集完成")
                        else:
                            item["content"] = ""
                        if CallBack is not None and super().FillBack(
                            CallBack=CallBack,
                            data=item,
                            Ext_Data={"mp_title":Mps_title,"mp_id":Mps_id},
                        ):
                            stats["inserted"] += 1
                    print(f"第{i+1}页爬取成功\n")
                    # 翻页
                    i += 1
                except requests.exceptions.Timeout:
                    print("Request timed out")
                    break
                except requests.exceptions.RequestException as e:
                    print(f"Request error: {e}")
                    break
                finally:
                    super().Item_Over(item={"mps_id":Mps_id,"mps_title":Mps_title},CallBack=Item_Over_CallBack)
        finally:
            if fallback_fetcher is not None:
                fallback_fetcher.Close()
            print_info(
                f"[api][summary] mp={Mps_title} pages={stats['pages']} items={stats['items']} "
                f"inserted={stats['inserted']} skipped_existing={stats['skipped_existing']} "
                f"list_fallback_pages={stats['list_fallback_pages']} "
                f"content_web_fallback={stats['content_web_fallback']}"
            )
        super().Over(CallBack=Over_CallBack)
        pass
