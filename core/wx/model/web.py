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
class MpsWeb(WxGather):

    # 重写 content_extract 方法
    def content_extract(self,  url, fetcher=None, keep_browser=False):
        try:
            from driver.wxarticle import Web as DefaultFetcher
            app = fetcher or DefaultFetcher
            r = app.get_article_content(url, keep_browser=keep_browser)
            if r!=None:
                text = r.get("content","")
                text=self.remove_common_html_elements(text)
                return  text
        except Exception as e:
            logger.error(e)
        return ""

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
    def get_Articles(self, faker_id:str=None,Mps_id:str=None,Mps_title="",CallBack=None,start_page:int=0,MaxPage:int=1,interval=10,Gather_Content=False,Item_Over_CallBack=None,Over_CallBack=None):
        super().Start(mp_id=Mps_id)
        if self.Gather_Content:
            Gather_Content=True
        print(f"Web浏览器模式,是否采集[{Mps_title}]内容：{Gather_Content}\n")
        # 请求参数
        url = "https://mp.weixin.qq.com/cgi-bin/appmsgpublish"
        count=5
        params = {
        "sub": "list",
        "sub_action": "list_ex",
        "begin":start_page,
        "count": count,
        "fakeid": faker_id,
        "token": self.token,
        "lang": "zh_CN",
        "f": "json",
        "ajax": 1
        }
        # 连接超时
        session=self.session
        stop_on_first_duplicate = cfg.get("gather.stop_on_first_duplicate", True)
        stats = {
            "pages": 0,
            "seen": 0,
            "inserted": 0,
            "skipped_existing": 0,
            "content_fetched": 0,
        }
        stop_feed = False
        article_fetcher = None
        if Gather_Content:
            from driver.wxarticle import WXArticleFetcher
            article_fetcher = WXArticleFetcher()
        # 起始页数
        i = start_page
        try:
            while True:
                if i >= MaxPage or stop_feed:
                    break
                begin = i * count
                params["begin"] = str(begin)
                print(f"第{i+1}页开始爬取\n")
                # 随机暂停几秒，避免过快的请求导致过快的被查到
                time.sleep(random.randint(0,interval))
                try:
                    headers = self.fix_header(url)
                    resp = session.get(url, headers=headers, params = params, verify=False)
                    
                    msg = resp.json()
                    self._cookies =resp.cookies
                    # 流量控制了, 退出
                    if msg['base_resp']['ret'] == 200013:
                        super().Error("frequencey control, stop at {}".format(str(begin)))
                        break
                    
                    if msg['base_resp']['ret'] == 200003:
                        super().Error("Invalid Session, stop at {}".format(str(begin)),code="Invalid Session")
                        break
                    if msg['base_resp']['ret'] != 0:
                        super().Error("错误原因:{}:代码:{}".format(msg['base_resp']['err_msg'],msg['base_resp']['ret']),code=msg['base_resp']['err_msg'])
                        break
                    items = self._extract_publish_items(msg)
                    # 如果返回的内容中为空则结束
                    if not items:
                        super().Error("all ariticle parsed")
                        break

                    stats["pages"] += 1
                    print_info(f"[web][list] page={i+1} items={len(items)}")
                    for item in items:
                        aid = item.get("aid", "")
                        title = item.get("title", "")
                        link = item.get("link", "")
                        if aid and super().HasGathered(aid):
                            continue

                        stats["seen"] += 1
                        item["id"] = aid
                        item["mp_id"] = Mps_id

                        if super().article_exists(article_id=item["id"], mp_id=Mps_id, url=link):
                            stats["skipped_existing"] += 1
                            print_info(f"[web][article] skip existing: {title}")
                            if stop_on_first_duplicate:
                                stop_feed = True
                                print_warning(f"[web][feed] stop on existing article: {title}")
                                break
                            continue

                        if Gather_Content:
                            item["content"] = self.content_extract(
                                link,
                                fetcher=article_fetcher,
                                keep_browser=True,
                            )
                            stats["content_fetched"] += 1
                            super().Wait(1,3,tips=f"{title} 采集完成")
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
            if article_fetcher is not None:
                article_fetcher.Close()
            print_info(
                f"[web][summary] mp={Mps_title} pages={stats['pages']} seen={stats['seen']} "
                f"inserted={stats['inserted']} skipped_existing={stats['skipped_existing']} "
                f"content_fetched={stats['content_fetched']}"
            )
        super().Over(CallBack=Over_CallBack)
        pass
