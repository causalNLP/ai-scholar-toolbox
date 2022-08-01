import re
import time
from typing import Union
from selenium import webdriver
from selenium.webdriver.chrome.options import ChromiumOptions
from selenium.webdriver.chromium.webdriver import ChromiumDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.errorhandler import NoSuchElementException


class ScholarGsSearch():
    """Class that handling searching on Google Scholar webpage using REST GET API."""
    def __init__(self, driver_path):
        self._authsearch = 'https://scholar.google.com/citations?hl=en&view_op=search_authors&mauthors={0}'
        self._gsidsearch = 'https://scholar.google.com/citations?hl=en&user={0}'
        self.print_true = False
        self.setup_webdriver(driver_path)

    def setup_webdriver(self, driver_path):
        """Setup the webdriver object."""
        options = ChromiumOptions()
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        self.driver = webdriver.Chrome(driver_path, options=options)
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })
    
    def change_name(self, name):
        new_name = name[1:].split('_')
        new_name[-1] = re.sub(r'[0-9]+', '', new_name[-1])
        new_name = ' '.join(new_name)
        return new_name

    def search_gsid(self, gs_sid: str, simple: bool = True):
        """Search scholar on Google Scholar based given gs_sid.
        
        Parameters
        ----------
        gs_sid : google scholar sid
        simple : whether return simple information without paper list.

        Returns
        -------
        scholar_dict_list : a list of dicts of responses.
        
        """
        url = self._gsidsearch.format(gs_sid)
        self.driver.get(url)
        scholar_dict = self._search_gsid_helper(self.driver, url, simple=simple)
        time.sleep(5)
        if scholar_dict is not None:
            
            return [scholar_dict]
        else:
            if self.print_true:
                print('[Info] No scholars found given gs_sid in search_gs.')
            return []
        
    def _search_gsid_helper(self, driver: ChromiumDriver, url: str, simple: bool = True):
        """Helper function for search_gsid."""

        def get_single_author(element):
            li=[]
            li.append(element.find_elements(By.TAG_NAME, "a")[0].get_attribute('href'))
            li.append(element.find_elements(By.TAG_NAME, "a")[0].get_attribute('textContent'))
            for i in element.find_elements(By.CLASS_NAME, "gsc_rsb_a_ext"):
                li.append(i.get_attribute('textContent'))
            return li

        html_first_class = driver.find_elements(By.CLASS_NAME, "gsc_g_hist_wrp")
        if (len(html_first_class)==0):
            if self.print_true:
                print("[Info] len(html_first_class)==0")
            return None
        idx_list = html_first_class[0].find_elements(By.CLASS_NAME, "gsc_md_hist_b")[0]
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
            if self.print_true:
                print("len(nameList)!=1")
            return None
        Researcher["name"] = nameList[0].text
        infoList = driver.find_elements(By.CLASS_NAME, 'gsc_prf_il')
        Researcher['organization'] = infoList[0].get_attribute('textContent')
        Researcher['domain_labels'] = [i.get_attribute('textContent').strip().lower() for i in infoList[2].find_elements(By.CLASS_NAME, 'gsc_prf_inta')]
        if not simple:
            button = driver.find_elements(By.CLASS_NAME, 'gs_btnPD')
            if (len(button) != 1):
                if self.print_true:
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

    def search_name(self, name: Union[str, list], query_dict: dict = None, top_n=3, simple=True):
        """Search on Google Scholar webpage given name.
        
        Parameters
        ----------
        name : name of the scholar.
        query_dict : a dict containing information of the scholar.
        top_n : select <top_n> candidates.
        simple : whether return simple information without paper list.

        Returns
        -------
        resp : list of candidate scholars, empty if no candidates are found.

        """
        from ScholarSearch import generate_or_keyword_list
        if type(name) is list:
            # current case
            name_list = [name[0], name[-1]]
            name = f'{name[0]} {name[-1]}' 
        elif type(name) is str:
            name_list = name.split(' ')
        else:
            raise TypeError('Argument "name" passed to ScholarGsSearch.search_name has the wrong type.')
        url_fragment = f'{name} '
        if query_dict is not None:
            # first try (name, email_suffix, position, organization) as url
            keyword_list = generate_or_keyword_list(query_dict)[0]
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
            url = self._authsearch.format(url_fragment_new)
            self.driver.get(url)
            time.sleep(5)
            scholar_list = self._search_name_helper(self.driver, name_list)
            # return scholar_list
            if len(scholar_list) > 0:
                if self.print_true:
                    print(f'[Info] Find {len(scholar_list)} scholars using query without gs_sid in step 1.')
                # return self._search_name_list_expand(scholar_list, simple=simple)
                return scholar_list
        
            # third try (name, position)
            if 'position' in keyword_list:
                url_fragment_new = url_fragment + keyword_list['position'] # + ' '
            url = self._authsearch.format(url_fragment_new)
            self.driver.get(url)
            time.sleep(5)
            scholar_list = self._search_name_helper(self.driver, name_list)
            # return scholar_list
            if len(scholar_list) > 0:
                if self.print_true:
                    print(f'[Info] Find {len(scholar_list)} scholars using query without gs_sid in step 2.')
                # return self._search_name_list_expand(scholar_list, simple=simple)
                return scholar_list

            # fourth try (name, organization)
            if 'organization' in keyword_list:
                url_fragment_new = url_fragment + keyword_list['organization'] # + ' '
            url = self._authsearch.format(url_fragment_new)
            self.driver.get(url)
            time.sleep(5)
            scholar_list = self._search_name_helper(self.driver, name_list)
            # return scholar_list
            if len(scholar_list) > 0:
                if self.print_true:
                    print(f'[Info] Find {len(scholar_list)} scholars using query without gs_sid in step 3.')
                # return self._search_name_list_expand(scholar_list, simple=simple)
                return scholar_list

        # finally, only search (name: firstname and lastname). If only one response returns, mark it as candidate
        url = self._authsearch.format(url_fragment)
        self.driver.get(url)
        time.sleep(5)
        scholar_list = self._search_name_helper(self.driver, name_list)
        if len(scholar_list) > 0 and len(scholar_list) <= top_n:
            if self.print_true:
                print(f'[Info] Find {len(scholar_list)} scholars using query without gs_sid in step 4.')
            # return self._search_name_list_expand(scholar_list, simple=simple)
            return scholar_list
        
        return []

    def _search_name_helper(self, driver, name_list):
        """Helper function of <self.search_name()>."""
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
        """Expand the name_list to full_name_list."""
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
