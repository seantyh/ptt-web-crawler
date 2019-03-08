import os
import re
import sys
import json
import requests
import time
from pathlib import Path
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger("PttWebCrawler.PttWebCrawler")
logger.setLevel("INFO")
SLEEP_TIME = 0.5
class PttWebCrawler:

    PTT_URL = 'https://www.ptt.cc'

    def __init__(self, data_path):
        self.data_path = Path(data_path)
        if not self.data_path.exists():
            self.data_path.mkdir(parents=True)        

    def parse_articles(self, start, end, board, path='.', timeout=3):
        filename = board + '-' + str(start) + '-' + str(end) + '.json'
        filename = os.path.join(path, filename)
        article_list = []
        for i in range(end-start+1):
            index = start + i
            print('Processing index:', str(index))
            resp = requests.get(
                url = self.PTT_URL + '/bbs/' + board + '/index' + str(index) + '.html',
                cookies={'over18': '1'}, timeout=timeout
            )
            if resp.status_code != 200:
                print('invalid url:', resp.url)
                continue
            soup = BeautifulSoup(resp.text, 'html.parser')
            divs = soup.find_all("div", "r-ent")
            for div in divs:
                try:
                    # ex. link would be <a href="/bbs/PublicServan/M.1127742013.A.240.html">Re: [問題] 職等</a>
                    if div.find('a'):
                        href = div.find('a')['href']
                    else:
                        continue
                    link = self.PTT_URL + href
                    article_id = re.sub('\.html', '', href.split('/')[-1])
                    article_list.append(self.parse(link, article_id, board))
                    time.sleep(SLEEP_TIME)
                except Exception as ex:
                    logger.error(ex)                                

        self.store(filename, article_list, "w") 
        return filename

    def parse_article(self, article_id, board, path='.'):
        link = self.PTT_URL + '/bbs/' + board + '/' + article_id + '.html'
        filename = board + '-' + article_id + '.json'
        filename = os.path.join(path, filename)
        article_data = self.parse(link, article_id, board)
        self.store(filename, article_data, 'w')
        return filename

    def parse(self, link, article_id, board, timeout=3):
        print('Processing article:', article_id)
        resp = requests.get(url=link, cookies={'over18': '1'}, timeout=timeout)
        if resp.status_code != 200:
            print('invalid url:', resp.url)
            return json.dumps({"error": "invalid url"}, sort_keys=True, ensure_ascii=False)
        soup = BeautifulSoup(resp.text, 'html.parser')
        main_content = soup.find(id="main-content")
        metas = main_content.select('div.article-metaline')
        author = ''
        title = ''
        date = ''
        if metas:
            author = metas[0].select('span.article-meta-value')[0].string if metas[0].select('span.article-meta-value')[0] else author
            title = metas[1].select('span.article-meta-value')[0].string if metas[1].select('span.article-meta-value')[0] else title
            date = metas[2].select('span.article-meta-value')[0].string if metas[2].select('span.article-meta-value')[0] else date

            # remove meta nodes
            for meta in metas:
                meta.extract()
            for meta in main_content.select('div.article-metaline-right'):
                meta.extract()

        # remove and keep push nodes
        pushes = main_content.find_all('div', class_='push')
        for push in pushes:
            push.extract()

        try:
            ip = main_content.find(text=re.compile(u'※ 發信站:'))
            ip = re.search('[0-9]*\.[0-9]*\.[0-9]*\.[0-9]*', ip).group()
        except:
            ip = "None"

        # 移除 '※ 發信站:' (starts with u'\u203b'), '◆ From:' (starts with u'\u25c6'), 空行及多餘空白
        # 保留英數字, 中文及中文標點, 網址, 部分特殊符號
        filtered = [ v for v in main_content.stripped_strings if v[0] not in [u'※', u'◆'] and v[:2] not in [u'--'] ]
        expr = re.compile(r'[^\u4e00-\u9fa5\u3002\uff1b\uff0c\uff1a\u201c\u201d\uff08\uff09\u3001\uff1f\u300a\u300b\s\w:/-_.?~%()]')
        for i in range(len(filtered)):
            filtered[i] = re.sub(expr, '', filtered[i])

        filtered = [_f for _f in filtered if _f]  # remove empty strings
        filtered = [x for x in filtered if article_id not in x]  # remove last line containing the url of the article
        content = ' '.join(filtered)
        content = re.sub(r'(\s)+', ' ', content)
        # print 'content', content

        # push messages
        p, b, n = 0, 0, 0
        messages = []
        for push in pushes:
            if not push.find('span', 'push-tag'):
                continue
            push_tag = push.find('span', 'push-tag').string.strip(' \t\n\r')
            push_userid = push.find('span', 'push-userid').string.strip(' \t\n\r')
            # if find is None: find().strings -> list -> ' '.join; else the current way
            push_content = push.find('span', 'push-content').strings
            push_content = ' '.join(push_content)[1:].strip(' \t\n\r')  # remove ':'
            push_ipdatetime = push.find('span', 'push-ipdatetime').string.strip(' \t\n\r')
            messages.append( {'push_tag': push_tag, 'push_userid': push_userid, 'push_content': push_content, 'push_ipdatetime': push_ipdatetime} )
            if push_tag == '推':
                p += 1
            elif push_tag == '噓':
                b += 1
            else:
                n += 1
        
        message_count = {
            'impact': p+b+n, 'polarity': p-b, 
            'positive': p, 'negative': b, "neutral": n}
        
        data = {
            'url': link,
            'board': board,
            'article_id': article_id,
            'article_title': title,
            'author': author,
            'date': date,
            'content': content,
            'ip': ip,
            'message_count': message_count,
            'messages': messages
        }

        return data

    def getLastPage(self, board, timeout=3):
        content = requests.get(
            url= 'https://www.ptt.cc/bbs/' + board + '/index.html',
            cookies={'over18': '1'}, timeout=timeout
        ).content.decode('utf-8')
        first_page = re.search(r'href="/bbs/' + board + '/index(\d+).html">&lsaquo;', content)
        if first_page is None:
            return 1
        return int(first_page.group(1)) + 1

    def store(self, filename, data, mode):        
        with open(self.data_path.joinpath(filename), 
                    mode, encoding='utf-8') as f:    
            json.dump(data, f, ensure_ascii=False, indent=2)

