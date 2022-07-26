import pandas as pd
import numpy as np
import pickle
import json
import typing
from typing import Union
import os
import re
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

class ScholarSearch():
    def __init__(self):
        self.get_profiles()
        self.search_78k = Scholar78kSearch()
        # self.search_gs = ScholarGsSearch()
        self.find_list = []
        self.cnt_find_gs_78k = 0
        self.cnt_find_gs_crawl = 0

    def reset(self):
        pass

    def get_profiles(self):
        with open('review_data/area_chair_id_to_profile.json') as file:
            chair_profile = json.load(file)
        with open('review_data/reviewer_id_to_profile.json') as file:
            reviewer_profile = json.load(file)
        self.openreview_profile = {}
        self.openreview_profile.update(chair_profile)
        self.openreview_profile.update(reviewer_profile)
        print(len(self.openreview_profile))

    def get_scholar(self, query: Union[str, dict], simple=True, verbose=False, top_n=3, print_true=True):
        """Get up to 3 relevant candidate scholars by searching over OpenReview profiles and 78k scholar dataset
        
        Parameters
        ----------
        query : the query containing the known scholar information.
        simple : True iff return simple information without paper list.

        Returns
        -------
        resp : list of candidate scholars, empty is no candidates found.

        """
        self.search_78k.simple = simple
        self.search_78k.verbose = verbose
        self.search_78k.print_true = print_true
        self.print_true = print_true
        self.reset()

        scholar_cnt = 0
        if type(query) is dict:
            # query is dict
            resp = self.search_dict(query, simple=simple, top_n=top_n)
        elif type(query) is str:
            # query is str
            resp = self.search_name(query, simple=simple, top_n=top_n)                
        else:
            raise TypeError(f'the argument "query" must be str or dict, not {type(query)}.')

        scholar_cnt = len(resp)
        if print_true:
            if scholar_cnt == 1:
                print(f'[Info] In total 1 scholar is found:')
            else:
                print(f'[Info] In total {scholar_cnt} scholars are found:')
            resp_str = json.dumps(resp, indent=2)
            print(resp_str)
        
        # search on gs_scholar
        # self.search_gs.get_scholar(query, simple=simple, verbose=verbose, top_n=top_n, print=print)
        return resp   
    
    def search_name(self, name, simple=True, verbose=False, top_n=3, from_dict=False, query_dict=None):
        """Search gs profile given name or OpenReview id.
        
        Parameters
        ----------
        name : the name ([first_name last_name])
        """

        self.search_78k.simple = simple
        self.search_78k.verbose = verbose
        name = name.strip()
        openreview_dict = None
        real_name = True
        # OpenReview id
        if ' ' not in name and name[0] == '~':
            # search over chair id
            if name in self.openreview_profile:
                openreview_dict = self.openreview_profile[name]
            # crawl http api response
            if openreview_dict is not None and not from_dict:
                # name
                real_name = False
                resp = self.search_dict(openreview_dict, simple=simple, top_n=top_n)
            else:
                # get real name
                or_name = name # string
                name = name[1:].split('_')
                name[-1] = re.sub(r'[0-9]+', '', name[-1]) # list
                # name = ' '.join(name) # e.g., Rachel K. E. Bellamy
        else:
            or_name = name.split(' ') # list
            # name string
        if real_name:
            # it inputs a real name (firstname, lastname)
            resp = self.search_78k.search_name(name)
            or_resp = self.get_or_scholars(or_name)
            if from_dict:
                print('Not find by gs_sid')
                resp = self.select_final_cands(resp, or_resp, top_n, query_dict=query_dict)
            else:
                resp = self.select_final_cands(resp, or_resp, top_n)
        return resp
    

    def get_or_scholars(self, or_name: Union[str, list]):
        """Get OpenReview candidate scholars list by name through http api response."""
        # format the name list to get OpenReview rest api response
        if type(or_name) is list:
            or_name_list = []
            if len(or_name) >= 2:
                id_list = []
                for idx, name_part in enumerate(or_name):
                    if idx == 0 or idx == len(or_name) - 1:
                        id_list.append(name_part.capitalize())
                    else:
                        if len(name_part) > 1:
                            id_list.append(f'{name_part[0].upper()}.') # middle name in abbreviate form
                        else:
                            id_list.append(name_part.upper())
                if len(id_list) == 2:
                    or_name_list.append(f'~{id_list[0]}_{id_list[-1]}')
                elif len(id_list) > 2:
                    or_name_list.append(f'~{id_list[0]}_{id_list[-1]}')
                    tmp_str = '_'.join(id_list)
                    or_name_list.append(f'~{tmp_str}')
            else:
                raise ValueError('Argument "or_name" passed to get_or_scholars is not a valid name list.')
        elif type(or_name) is str:
            or_name_list = [or_name]
        else:
            raise TypeError(f'Argument "or_name" passed to get_or_scholars has the wrong type.')
        del or_name

        # get request response
        go_ahead = True
        resp_list = []
        for name in or_name_list:
            if name[-1].isnumeric():
                name_cur = name
                go_ahead = False
                name_cur_cnt = 1
            else:
                name_cur_cnt = 1
                name_cur = f'{name}{name_cur_cnt}'

            # set accumulative count
            acc_cnt = 0
            while acc_cnt <= 1:
                response = requests.get(f'https://openreview.net/profile?id={name_cur}')
                time.sleep(1)

                if not response.ok:
                    acc_cnt += 1
                else:
                    soup = BeautifulSoup(response.content.decode('utf-8'), 'html.parser')
                    resp_list.append(json.loads(soup.find_all('script', id="__NEXT_DATA__")[0].string))
                name_cur_cnt += 1
                name_cur = f'{name}{name_cur_cnt}'
                if not go_ahead:
                    break
        if self.print_true:
            if len(resp_list) != 1:
                print(f'[Info] Found {len(resp_list)} scholars using OpenReview REST API.')
            else:
                print(f'[Info] Found 1 scholar using OpenReview REST API.')
        if self.search_78k.verbose:
            print(resp_list)
        return resp_list 
        # NOTE: the dict in this list is in a different format than the dict from OpenReview dataset.

    def select_final_cands(self, resp, or_resp, top_n, query_dict=None):
        """Select final candidates according to the response from OpenReview and 78k data."""
        # get useful data from or_resp
        if query_dict is None:
            or_keyword_list = []
            for or_resp_item in or_resp:
                or_keyword_dict = {}
                # url
                url = None
                for link in or_resp_item['props']['pageProps']['profile']['links']:
                    if link['name'] == 'Google Scholar':
                        url = link['url']
                        break
                if url is not None:
                    # get gs_sid
                    gs_id = url.split('user=', 1)[1][:12]
                    or_keyword_dict['gs_sid'] = gs_id
                else:
                    or_keyword_dict['gs_sid'] = ''
                
                # domain_tags
                domain_tags = []
                if 'expertise' in or_resp_item['props']['pageProps']['profile']:
                    for keyword in or_resp_item['props']['pageProps']['profile']['expertise']:
                        for key in keyword['keywords']:
                            key = key.strip().lower().replace(' ', '_')                        
                            domain_tags.append(key)
                or_keyword_dict['domain_tags'] = domain_tags

                # relations
                coauthors = []
                if 'relations' in or_resp_item['props']['pageProps']['profile']:
                    for relation in or_resp_item['props']['pageProps']['profile']['relations']:
                        coauthors.append(relation['name'])
                or_keyword_dict['coauthors'] = coauthors

                or_keyword_list.append(or_keyword_dict)
        else:
            or_keyword_list = []
            or_keyword_dict = {}
            or_keyword_dict['gs_sid'] = ''
            domain_tags = []
            if 'expertise' in query_dict['profile']['content']:
                for keyword in query_dict['profile']['content']['expertise']:
                    for key in keyword['keywords']:
                        key = key.strip().lower().replace(' ', '_')
                        domain_tags.append(key)
            or_keyword_dict['domain_tags'] = domain_tags

            coauthors = []
            if 'relations' in query_dict['profile']['content']:
                for relation in query_dict['profile']['content']['relations']:
                    coauthors.append(relation['name'])
            or_keyword_dict['coauthors'] = coauthors

            or_keyword_list.append(or_keyword_dict)


        rank = {}
        for idx_cand, cand in enumerate(resp):
            rank[idx_cand] = []
            gs_sid_flag = 0
            cnt_true = [0] * len(or_keyword_list) 
            cnt_all = 0
            cnt_true_rel = [0] * len(or_keyword_list) 
            cnt_all_rel = 0
            for idx_or_scholar, or_scholar in enumerate(or_keyword_list):
                # gs_sid
                if cand['gs_sid'] == or_scholar['gs_sid']: 
                    gs_sid_flag = 1

                # domain_tags
                if cand['domain_labels'] is not None:
                    for cand_domain_tag in cand['domain_labels']:
                        cnt_all += 1
                        for or_domain_tag in or_scholar['domain_tags']:
                            if cand_domain_tag == or_domain_tag:
                                cnt_true[idx_or_scholar] += 1
                
                
                # relations
                cnt_all_rel = 0
                if cand['co_authors'] is not None:
                    for cand_coauth in cand['co_authors']:
                        cnt_all_rel += 1
                        for or_coauth in or_scholar['coauthors']:
                            if cand_coauth == or_coauth[1]:
                                cnt_true_rel[idx_or_scholar] += 1
                
            # get the rank list
            # gs_sid
            if gs_sid_flag:
                rank[idx_cand].append(1)
            else:
                rank[idx_cand].append(0)
            
            # domain_tags
            for i in range(len(cnt_true)):
                if cnt_all == 0:
                    cnt_true[i] = 0
                else:
                    cnt_true[i] = cnt_true[i] / cnt_all
            rank[idx_cand].append(max(cnt_true))

            # relations
            for i in range(len(cnt_true_rel)):
                if cnt_all_rel == 0:
                    cnt_true_rel[i] = 0
                else:
                    cnt_true_rel[i] = cnt_true_rel[i] / cnt_all_rel
            rank[idx_cand].append(max(cnt_true_rel))
        
        # select final candidate
        final_idx = []
        for rank_idx in rank:
            if rank[rank_idx][0] == 1:
                final_idx.append(rank_idx)
        
        if len(final_idx) < top_n:
            domain_tag_rank = []
            relation_rank = []
            for rank_idx in rank:
                domain_tag_rank.append(rank[rank_idx][1])
                relation_rank.append(rank[rank_idx][2])
            domain_tag_idxes = np.argsort(domain_tag_rank)
            relation_idxes = np.argsort(relation_rank)
            for idx in relation_idxes:
                # if relation_rank[idx] == 0:
                #     break
                if len(final_idx) < top_n:
                    if idx not in final_idx:
                        final_idx.append(idx)
                else:
                    break
            for idx in domain_tag_idxes:
                # if domain_tag_rank[idx] == 0:
                #     break
                if len(final_idx) < top_n:
                    if idx not in final_idx:
                        final_idx.append(idx)
                else:
                    break
        resp = [resp[i] for i in final_idx]
        return resp

    def search_dict(self, query_dict, simple=True, verbose=False, top_n=3):
        self.search_78k.simple = simple
        self.search_78k.verbose = verbose
        # gs_sid
        if 'gscholar' in query_dict['profile']['content'] and 'user=' in query_dict['profile']['content']['gscholar']:
            gs_id = query_dict['profile']['content']['gscholar'].split('user=', 1)[1][:12]
            name_df = self.search_78k.df.loc[self.search_78k.df['gs_sid'] == gs_id].copy()
            if name_df.shape[0] != 0:
                self.cnt_find_gs_78k += 1
                return self.search_78k._deal_with_simple(name_df)
            else:
                self.cnt_find_gs_crawl += 1
                self.find_list.append(query_dict)
                return []
        
        # search_name
        return self.search_name(query_dict['profile']['id'], simple=simple, top_n=top_n, from_dict=True, query_dict=query_dict)




class Scholar78kSearch():
    def __init__(self):
        self.get_78kdata()
        self.simple = False
        self.verbose = False
        self.print_true = True

    def get_78kdata(self, source='gself.drive'):
        if source == 'gself.drive':
            import gdown
            if not os.path.exists('source'):
                os.mkdir('source')
            if not os.path.exists('source/gs_scholars_all.npy'):
                gdown.download(
                    'https://self.drive.google.com/uc?id=1eEKhUQyfCNl-wt9yLwEEQN8QSnlbmGtz',
                    'source/gs_scholars_all.npy'
                )
        self.df = pd.DataFrame.from_records(np.load('source/gs_scholars_all.npy', allow_pickle=True))
    
    def search_name(self, name: Union[str, list]):
        if type(name) is list:
            name_list = [name[0], name[-1]]
            name = f'{name[0]} {name[-1]}' 
        elif type(name) is str:
            name_list = name.split(' ')
        else:
            raise TypeError(f'Argument "name" passed to Scholar78kSearch.search_name has the wrong type.')
        df_row = self._search_name_bool(name, name_list)
        if self.print_true:
            print(f'[Info] Found {df_row.shape[0]} scholars are in the same name.')
        if self.verbose:
            print(df_row)
        return self._deal_with_simple(df_row)
        # return df_row

    def _deal_with_simple(self, df_row):
        if self.simple:
            df_row = df_row.loc[:, df_row.columns != 'papers']
        df_row = df_row.drop(['co_authors_all'], axis=1)
        return df_row.to_dict(orient='records')

    def _search_name_bool(self, name, name_list):
        """Helper function of search_name

        Returns
        -------
        Boolean : found or not.
        DataFrame : if find else None.
        """
        # find the scholar in our dataset
        name_df = self.df.loc[self.df['name'] == name].copy()
        name_list_df = self.df.loc[self.df['name'].str.contains(pat = f'^{name_list[0].capitalize()} .*{name_list[-1].capitalize()}', regex=True, case=False)].copy()
        return pd.concat([name_df, name_list_df]).drop_duplicates(subset=['url']).reset_index(drop=True)
    

class ScholarGsSearch():
    def __init__(self):
        self.setup()

    def setup(self):
        self._authsearch = 'https://scholar.google.com/citations?hl=en&view_op=search_authors&mauthors={0}'
        self._gsidsearch = 'https://scholar.google.com/citations?hl=en&user={0}'
        options = Options()
        # 隐藏 正在受到自动软件的控制 这几个字
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        self.driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)

        # 修改 webdriver 值
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
        if 'gscholar' in query_dict['profile']['content']['gscholar'] and 'user=' in query_dict['profile']['content']['gscholar']:
            gs_id = query_dict['profile']['content']['gscholar'].split('user=', 1)[1][:12]
            return self.search_gsid(gs_id)
        position, school = None, None
        if 'position' in query_dict['profile']['content']['history'][0]:
            position = query_dict['profile']['content']['history'][0]['position']
        if ('institution' in query_dict['profile']['content']['history'][0] and 
            'name' in query_dict['profile']['content']['history'][0]['institution']):
            school = query_dict['profile']['content']['history'][0]['institution']['name']
        url_item.append('authsearch')
        url_item.append(self._authsearch.format(requests.utils.quote(name)))

        return url_item

    def search_gsid(self, gs_id):
        url = self._gsidsearch.format(gs_id)
        # resp = requests.get(url)
        # if not resp.ok:
        #     return {}
        # resp_str = resp.content.decode('utf-8', errors='ignore')
        # soup = BeautifulSoup(resp_str, 'html.parser')
        
        self.driver.get(url)
        scholar_dict = self._search_gsid_helper(self.driver, url)
        time.sleep(10)
        return scholar_dict
        
    def _search_gsid_helper(self, driver, url):
        def get_signle_author(element):
            li=[]
            li.append(element.find_elements_by_tag_name("a")[0].get_attribute('href'))
            li.append(element.find_elements_by_tag_name("a")[0].get_attribute('textContent'))
            for i in element.find_elements_by_class_name("gsc_rsb_a_ext"):
                li.append(i.get_attribute('textContent'))
            return li
        qwq = driver.find_elements_by_class_name("gsc_g_hist_wrp")
        if (len(qwq)==0):
            return None
        idx_list = qwq[0].find_elements_by_class_name("gsc_md_hist_b")[0]
        years =  [i.get_attribute('textContent') for i in idx_list.find_elements_by_class_name("gsc_g_t")]
        cites =  [i.get_attribute('innerHTML') for i in idx_list.find_elements_by_class_name("gsc_g_al")]
        rsb = driver.find_elements_by_class_name("gsc_rsb")[0]
        Citations_table=[i.get_attribute('textContent') for i in  rsb.find_elements_by_class_name("gsc_rsb_std")]
        Co_authors = rsb.find_elements_by_class_name("gsc_rsb_a")
        if len(Co_authors) == 0:
            Co_authors = None
        else:
            Co_authors = [get_signle_author(i) for i in rsb.find_element_by_class_name("gsc_rsb_a").find_elements_by_class_name("gsc_rsb_a_desc")]

        Reseacher = {"url": url}
        Reseacher["co_authors"] = Co_authors
        Reseacher["citations_table"] = Citations_table
        Reseacher["cites"] = {"years":years, "cites":cites}
        nameList = driver.find_elements_by_id("gsc_prf_in")
        if (len(nameList) != 1):
            return None
        Reseacher["name"] = nameList[0].text
        infoList = driver.find_elements_by_class_name('gsc_prf_il')
        infoList = [i.get_attribute('innerHTML') for i in infoList]
        Reseacher["extra_info"] = infoList
        button = driver.find_elements_by_class_name('gs_btnPD')
        if (len(button) != 1):
            print("qnq")
            return None
        while (button[0].is_enabled()):
            while (button[0].is_enabled()):
                while (button[0].is_enabled()):
                    button[0].click()
                    time.sleep(5)
                time.sleep(1)
            time.sleep(2)
        papers = []
        items = driver.find_elements_by_class_name('gsc_a_tr')
        for i in items:
            item = i.find_element_by_class_name('gsc_a_at')
            url = item.get_attribute("href")
            paper_info=[j.text for j in i.find_elements_by_class_name('gs_gray')]
            cite = i.find_element_by_class_name('gsc_a_ac')
            year = i.find_element_by_class_name('gsc_a_y').find_element_by_class_name("gsc_a_h").text
            papers.append([url, item.text, 
                            paper_info,
                        cite.text, cite.get_attribute("href"),
                        year])
        Reseacher["papers"] = papers
        def generate_signle_coauthor(element):
            coauthor_dict = {
                "name":element.find_elements_by_class_name('gs_ai_name')[0].get_attribute('textContent'),
                "url":element.find_elements_by_class_name('gs_ai_pho')[0].get_attribute('href'),
                "description":element.get_attribute('innerHTML'),
            }
            return coauthor_dict
        extra_coauthors = driver.find_elements_by_class_name("gsc_ucoar")
        Reseacher['extra_co_authors'] = [generate_signle_coauthor(i) for i in extra_coauthors]
        return Reseacher

    def search_name(self, name: Union[str, list]):
        pass

    def _deal_with_simple(self, gs_dict):
        pass
    