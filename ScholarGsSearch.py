import re
import time
from typing import Union
from selenium import webdriver
from selenium.webdriver.chrome.options import ChromiumOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.errorhandler import NoSuchElementException
from ScholarSearch import generate_or_keyword_list

class ScholarGsSearch():
    def __init__(self):
        self.setup()

    def setup(self):
        self._authsearch = 'https://scholar.google.com/citations?hl=en&view_op=search_authors&mauthors={0}'
        self._gsidsearch = 'https://scholar.google.com/citations?hl=en&user={0}'
        options = ChromiumOptions()
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        self.driver = webdriver.Chrome('../chromedriver', options=options)
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })
    
    def change_name(self, name):
        new_name = name[1:].split('_')
        new_name[-1] = re.sub(r'[0-9]+', '', new_name[-1])
        new_name = ' '.join(new_name)
        return new_name
    
    def get_scholar(self, key, query_dict):
        url_item = []
        name = self.change_name(key)
        if 'gscholar' in query_dict['profile']['content'] and 'user=' in query_dict['profile']['content']['gscholar']:
            tmp_gs_sid = query_dict['profile']['content']['gscholar'].split('user=', 1)[1]
            if len(tmp_gs_sid) >= 12:
                gs_sid = tmp_gs_sid[:12]
                return self.search_gsid(gs_sid)
        position, school = None, None
        if 'position' in query_dict['profile']['content']['history'][0]:
            position = query_dict['profile']['content']['history'][0]['position']
        if ('institution' in query_dict['profile']['content']['history'][0] and 
            'name' in query_dict['profile']['content']['history'][0]['institution']):
            school = query_dict['profile']['content']['history'][0]['institution']['name']


    def search_gsid(self, gs_sid, simple=True):
        url = self._gsidsearch.format(gs_sid)
        # resp = requests.get(url)
        # if not resp.ok:
        #     return {}
        # resp_str = resp.content.decode('utf-8', errors='ignore')
        # soup = BeautifulSoup(resp_str, 'html.parser')
        
        self.driver.get(url)
        scholar_dict = self._search_gsid_helper(self.driver, url, simple=simple)
        time.sleep(5)
        if scholar_dict is not None:
            
            return [scholar_dict]
        else:
            print('However, no scholars found.')
            return []
        
    def _search_gsid_helper(self, driver, url, simple=True):
        def get_single_author(element):
            li=[]
            li.append(element.find_elements(By.TAG_NAME, "a")[0].get_attribute('href'))
            li.append(element.find_elements(By.TAG_NAME, "a")[0].get_attribute('textContent'))
            for i in element.find_elements(By.CLASS_NAME, "gsc_rsb_a_ext"):
                li.append(i.get_attribute('textContent'))
            return li

        qwq = driver.find_elements(By.CLASS_NAME, "gsc_g_hist_wrp")
        if (len(qwq)==0):
            print("len(qwq)==0")
            return None
        idx_list = qwq[0].find_elements(By.CLASS_NAME, "gsc_md_hist_b")[0]
        years =  [i.get_attribute('textContent') for i in idx_list.find_elements(By.CLASS_NAME, "gsc_g_t")]
        cites =  [i.get_attribute('innerHTML') for i in idx_list.find_elements(By.CLASS_NAME, "gsc_g_al")]
        rsb = driver.find_elements(By.CLASS_NAME, "gsc_rsb")[0]
        Citations_table=[i.get_attribute('textContent') for i in  rsb.find_elements(By.CLASS_NAME, "gsc_rsb_std")]
        Co_authors = rsb.find_elements(By.CLASS_NAME, "gsc_rsb_a")
        if len(Co_authors) == 0:
            Co_authors = None
        else:
            Co_authors = [get_single_author(i) for i in rsb.find_element(By.CLASS_NAME, "gsc_rsb_a").find_elements(By.CLASS_NAME, "gsc_rsb_a_desc")]

        Researcher = {"url": url}
        gs_sid = None
        if 'user=' in url:
            tmp_gs_sid = url.split('user=', 1)[1]
            if len(tmp_gs_sid) >= 12:
                gs_sid = tmp_gs_sid[:12]
        Researcher['gs_sid'] = gs_sid
        Researcher["coauthors"] = Co_authors
        Researcher["citation_table"] = [Citations_table[0], Citations_table[2]]
        Researcher["cites"] = {"years":years, "cites":cites}
        nameList = driver.find_elements(By.ID, "gsc_prf_in")
        if (len(nameList) != 1):
            print("len(nameList)!=1")
            return None
        Researcher["name"] = nameList[0].text
        infoList = driver.find_elements(By.CLASS_NAME, 'gsc_prf_il')
        Researcher['organization'] = infoList[0].get_attribute('textContent')
        Researcher['domain_labels'] = [i.get_attribute('textContent').strip().lower() for i in infoList[2].find_elements(By.CLASS_NAME, 'gsc_prf_inta')]
        if not simple:
            button = driver.find_elements(By.CLASS_NAME, 'gs_btnPD')
            if (len(button) != 1):
                print("qnq")
                print("len(button)!=1")
                return None
            while (button[0].is_enabled()):
                while (button[0].is_enabled()):
                    while (button[0].is_enabled()):
                        button[0].click()
                        time.sleep(5)
                    time.sleep(1)
                time.sleep(2)
            papers = []
            items = driver.find_elements(By.CLASS_NAME, 'gsc_a_tr')
            for i in items:
                item = i.find_element(By.CLASS_NAME, 'gsc_a_at')
                url = item.get_attribute("href")
                paper_info=[j.text for j in i.find_elements(By.CLASS_NAME, 'gs_gray')]
                cite = i.find_element(By.CLASS_NAME, 'gsc_a_ac')
                year = i.find_element(By.CLASS_NAME, 'gsc_a_y').find_element(By.CLASS_NAME, "gsc_a_h").text
                papers.append([url, item.text, 
                                paper_info,
                            cite.text, cite.get_attribute("href"),
                            year])
            Researcher["papers"] = papers

        def generate_single_coauthor(element):
            coauthor_dict = {
                "name":element.find_elements(By.CLASS_NAME, 'gs_ai_name')[0].get_attribute('textContent'),
                "url":element.find_elements(By.CLASS_NAME, 'gs_ai_pho')[0].get_attribute('href'),
                "description":element.get_attribute('innerHTML'),
            }
            return coauthor_dict
        extra_coauthors = driver.find_elements(By.CLASS_NAME, "gsc_ucoar")
        Researcher['extra_co_authors'] = [generate_single_coauthor(i) for i in extra_coauthors]
        return Researcher

    def search_name(self, name: Union[str, list], query_dict=None, wo_full=True, top_n=3, simple=True):
        if type(name) is list:
            # current case
            name_list = [name[0], name[-1]]
            name = f'{name[0]} {name[-1]}' 
        elif type(name) is str:
            name_list = name.split(' ')
        else:
            raise TypeError('Argument "name" passed to ScholarGsSearch.search_name has the wrong type.')
        # first try (name, email_suffix, position, organization) as url
        url_fragment = f'{name} '
        keyword_list = generate_or_keyword_list(None, query_dict)[0]
        url_fragment_new = url_fragment
        # if 'email_suffix' in keyword_list:
        #     url_fragment_new = url_fragment_new + keyword_list['email_suffix'] + ' '
        # if 'position' in keyword_list:
        #     url_fragment_new = url_fragment_new + keyword_list['position'] + ' '
        # if 'organization' in keyword_list:
        #     url_fragment_new = url_fragment_new + keyword_list['organization'] + ' '

        # url = self._authsearch.format(url_fragment_new)
        # self.driver.get(url)
        # time.sleep(5)
        # scholar_list = self._search_name_helper(self.driver, name_list)
        # if len(scholar_list) > 0:
        #     if wo_full:
        #         return scholar_list
        #     else:
        #         return self._search_name_list_expand(scholar_list, simple=simple)
        
        # second try (name, email_suffix)
        if 'email_suffix' in keyword_list:
            url_fragment_new = url_fragment + keyword_list['email_suffix'] # + ' '
        # print(url_fragment_new)
        url = self._authsearch.format(url_fragment_new)
        # print(url)
        # print(keyword_list)
        self.driver.get(url)
        time.sleep(5)
        scholar_list = self._search_name_helper(self.driver, name_list)
        # return scholar_list
        if len(scholar_list) > 0:
            print(f'[Info] Find {len(scholar_list)} scholars using query without gs_sid in step 1')
            if wo_full:
                return scholar_list
            else:
                return self._search_name_list_expand(scholar_list, simple=simple)
    
        # third try (name, position)
        if 'position' in keyword_list:
            url_fragment_new = url_fragment + keyword_list['position'] # + ' '
        url = self._authsearch.format(url_fragment_new)
        self.driver.get(url)
        time.sleep(5)
        scholar_list = self._search_name_helper(self.driver, name_list)
        # return scholar_list
        if len(scholar_list) > 0:
            print(f'[Info] Find {len(scholar_list)} scholars using query without gs_sid in step 2')
            if wo_full:
                return scholar_list
            else:
                return self._search_name_list_expand(scholar_list, simple=simple)

        # fourth try (name, organization)
        if 'organization' in keyword_list:
            url_fragment_new = url_fragment + keyword_list['organization'] # + ' '
        url = self._authsearch.format(url_fragment_new)
        self.driver.get(url)
        time.sleep(5)
        scholar_list = self._search_name_helper(self.driver, name_list)
        # return scholar_list
        if len(scholar_list) > 0:
            print(f'[Info] Find {len(scholar_list)} scholars using query without gs_sid in step 3')
            if wo_full:
                return scholar_list
            else:
                return self._search_name_list_expand(scholar_list, simple=simple)

        # finally, only search (name: firstname and lastname). If only one response returns, mark it as candidate
        url = self._authsearch.format(url_fragment)
        self.driver.get(url)
        time.sleep(5)
        scholar_list = self._search_name_helper(self.driver, name_list)
        if len(scholar_list) > 0 and len(scholar_list) <= top_n:
            print(f'[Info] Find {len(scholar_list)} scholars using query without gs_sid in step 4')
            if wo_full:
                return scholar_list
            else:
                return self._search_name_list_expand(scholar_list, simple=simple)
        
        return []

    def _search_name_helper(self, driver, name_list):
        # iterate over searched list, find dicts that contains the name (including)
        useful_info_list = driver.find_elements(By.CLASS_NAME, 'gs_ai_t')
        useful_info_ext_list = []
        if len(useful_info_list) != 0:
            for scholar_webdriver in useful_info_list:
                name = scholar_webdriver.find_element(By.CLASS_NAME, 'gs_ai_name').get_attribute('textContent').strip()
                # check whether name is correct
                not_a_candidate = False
                for name_fragment in name_list:
                    if name_fragment.lower() not in name.lower():
                        not_a_candidate = True
                        break
                if not_a_candidate:
                    continue
                
                # grab all the other information
                pos_org = scholar_webdriver.find_element(By.CLASS_NAME, 'gs_ai_aff').get_attribute('textContent').strip()
                email_str = scholar_webdriver.find_element(By.CLASS_NAME, 'gs_ai_eml').get_attribute('textContent').strip()
                cite = scholar_webdriver.find_element(By.CLASS_NAME, 'gs_ai_cby').get_attribute('textContent').strip()
                url = scholar_webdriver.find_element(By.CLASS_NAME, 'gs_ai_name').find_element(By.TAG_NAME, 'a').get_attribute('href').strip()
                domain_labels = scholar_webdriver.find_element(By.CLASS_NAME, 'gs_ai_int').find_elements(By.CLASS_NAME, 'gs_ai_ont_int')
                for idx, domain in enumerate(domain_labels):
                    domain_labels[idx] = domain.get_attribute('textContent').strip().lower()

                # continue processing
                gs_sid = None
                if 'user=' in url:
                    tmp_gs_sid = url.split('user=', 1)[1]
                    if len(tmp_gs_sid) >= 12:
                        gs_sid = tmp_gs_sid[:12]
                # print(email_str)
                # return [scholar_webdriver]
                
                # print(type(email_str))
                if email_str is not None and email_str != '':
                    match = re.search(r'[\w-]+\.[\w.-]+', email_str)
                    email_str = match.group(0)

                cites = [int(s) for s in cite.split() if s.isdigit()]
                useful_info_ext_list.append({
                    'name': name,
                    'pos_org': pos_org,
                    'email': email_str,
                    'cite': cites[0] if len(cites)>0 else None,
                    'url': url,
                    'gs_sid': gs_sid,
                    'domain_labels': domain_labels
                })
        return useful_info_ext_list
        
    def _search_name_list_expand(self, scholar_list, simple=True):
        new_scholar_list = []
        for scholar in scholar_list:
            if 'gs_sid' in scholar:
                url = self._gsidsearch.format(scholar['gs_sid'])
                self.driver.get(url)
                scholar_dict = self._search_gsid_helper(self.driver, url, simple=simple)
                if scholar_dict is not None:
                    new_scholar_list.append(scholar_dict)
                time.sleep(5)
        return new_scholar_list
