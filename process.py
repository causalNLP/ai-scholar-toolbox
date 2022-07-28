import pandas as pd
import numpy as np
import pickle
import json
import typing
from typing import Union
import os
import re
import time
import sys
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import ChromiumOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.errorhandler import NoSuchElementException

class ScholarSearch():
    def __init__(self):
        self.get_profiles()
        self.search_78k = Scholar78kSearch()
        self.search_gs = ScholarGsSearch()
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

    def get_scholar(self, query: Union[str, dict], simple=True, verbose=False, top_n=3, print_true=True, wo_full=True):
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
    
    def search_name(self, name, simple=True, verbose=False, top_n=3, from_dict=False, query_dict=None, wo_full=True):
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
            # TODO: integrate resp_gs with resp
            if from_dict:
                print('Not find by gs_sid')
                or_resp = None
                resp_gs = self.search_gs.search_name(name, query_dict, wo_full=wo_full, simple=simple)
                resp = self.select_final_cands(resp, or_resp, top_n, query_dict=query_dict, resp_gs_prop={'wo_full': wo_full, 'resp_gs': resp_gs})
            else:
                or_resp = self.get_or_scholars(or_name)
                # TODO: resp_gs for only searching name is not implemented
                resp = self.select_final_cands(resp, or_resp, top_n, simple=simple)
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

    def select_final_cands(self, resp, or_resp, top_n, query_dict=None, resp_gs_prop=None, simple=True):
        """Select final candidates according to the response from OpenReview and 78k data."""
        # get useful data from or_resp
        or_keyword_list = generate_or_keyword_list(or_resp, query_dict)

        # merge resp with resp_gs
        if resp_gs_prop is not None:
            wo_full = resp_gs_prop['wo_full']
            resp_gs = resp_gs_prop['resp_gs']
            if query_dict is None:
                raise NotImplementedError
            for resp_gs_item in resp_gs:
                find_flag = False
                # gs_sid
                for resp_item in resp:
                    if resp_gs_item['gs_sid'] == resp_item['gs_sid']:
                        find_flag = True
                        break
                if find_flag:
                    continue
                # construct new prep
                if wo_full:
                    # generate full dict
                    self.search_gs.driver.get(resp_gs_item['url'])
                    time.sleep(5)
                    resp_gs_full_item = self.search_gs._search_gsid_helper(self.search_gs.driver, resp_gs_item['url'], simple=simple)
                    resp.append(resp_gs_full_item)
                else:
                    resp.append(resp_gs_item)
        # calculate rankings
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
                if 'gs_sid' in cand:
                    if cand['gs_sid'] == or_scholar['gs_sid']: 
                        gs_sid_flag = 1

                # domain_labels
                if cand['domain_labels'] is not None:
                    # if idx_cand == 6:
                    #     print(cand['domain_labels'])
                    #     print(or_scholar['domain_labels'])
                    for cand_domain_tag in cand['domain_labels']:
                        cnt_all += 1
                        for or_domain_tag in or_scholar['domain_labels']:
                            if cand_domain_tag == or_domain_tag:
                                cnt_true[idx_or_scholar] += 1
                
                
                # relations
                cnt_all_rel = 0
                # print(cand)
                if cand['coauthors'] is not None:
                    # if idx_cand == 6:
                    #     print(cand['coauthors'])
                    #     print(or_scholar['coauthors'])
                    for cand_coauth in cand['coauthors']:
                        cnt_all_rel += 1
                        for or_coauth in or_scholar['coauthors']:
                            if or_coauth == cand_coauth[1]:
                                cnt_true_rel[idx_or_scholar] += 1
                
            # get the rank list
            # gs_sid
            if gs_sid_flag:
                rank[idx_cand].append(1)
            else:
                rank[idx_cand].append(0)
            
            # domain_labels
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
            # if idx_cand == 6:
            #     print(cnt_true, cnt_true_rel, cnt_all, cnt_all_rel)
        
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
            domain_tag_idxes = np.argsort(domain_tag_rank)[::-1]
            relation_idxes = np.argsort(relation_rank)[::-1]
            for idx in relation_idxes:
                if relation_rank[idx] == 0:
                    break
                if len(final_idx) < top_n:
                    if idx not in final_idx:
                        final_idx.append(idx)
                else:
                    break
            for idx in domain_tag_idxes:
                if domain_tag_rank[idx] == 0:
                    break
                if len(final_idx) < top_n:
                    if idx not in final_idx:
                        final_idx.append(idx)
                else:
                    break
        # print(resp)
        # print(or_keyword_list)
        # print(rank)
        # print(final_idx)
        resp = [resp[i] for i in final_idx]
        return resp

    def search_dict(self, query_dict, simple=True, verbose=False, top_n=3):
        self.search_78k.simple = simple
        self.search_78k.verbose = verbose
        # gs_sid
        if 'gscholar' in query_dict['profile']['content'] and 'user=' in query_dict['profile']['content']['gscholar']:
            gs_sid = query_dict['profile']['content']['gscholar'].split('user=', 1)[1][:12]
            name_df = self.search_78k.df.loc[self.search_78k.df['gs_sid'] == gs_sid].copy()
            if name_df.shape[0] != 0:
                self.cnt_find_gs_78k += 1
                return self.search_78k._deal_with_simple(name_df)
            else:
                self.cnt_find_gs_crawl += 1
                self.find_list.append(query_dict)
                return self.search_gs.search_gsid(gs_sid, simple=simple)
        
        # search_name
        return self.search_name(query_dict['profile']['id'], simple=simple, top_n=top_n, from_dict=True, query_dict=query_dict, wo_full=True)

def generate_or_keyword_list(or_resp, query_dict):
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
                gs_sid = url.split('user=', 1)[1][:12]
                or_keyword_dict['gs_sid'] = gs_sid
            else:
                or_keyword_dict['gs_sid'] = ''
            
            # domain_labels
            domain_labels = []
            if 'expertise' in or_resp_item['props']['pageProps']['profile']:
                for keyword in or_resp_item['props']['pageProps']['profile']['expertise']:
                    for key in keyword['keywords']:
                        key = key.strip().lower().replace(' ', '_')                        
                        domain_labels.append(key)
            or_keyword_dict['domain_labels'] = domain_labels

            # relations
            coauthors = []
            if 'relations' in or_resp_item['props']['pageProps']['profile']:
                for relation in or_resp_item['props']['pageProps']['profile']['relations']:
                    coauthors.append(relation['name'])
            or_keyword_dict['coauthors'] = coauthors

            # TODO: update to the same status as in "else" statement

            or_keyword_list.append(or_keyword_dict)
    else:
        or_keyword_list = []
        or_keyword_dict = {}
        or_keyword_dict['gs_sid'] = ''
        domain_labels = []
        if 'expertise' in query_dict['profile']['content']:
            for keyword in query_dict['profile']['content']['expertise']:
                for key in keyword['keywords']:
                    key = key.strip().lower()
                    domain_labels.append(key)
        or_keyword_dict['domain_labels'] = domain_labels

        coauthors = []
        if 'relations' in query_dict['profile']['content']:
            for relation in query_dict['profile']['content']['relations']:
                coauthors.append(relation['name'])
        or_keyword_dict['coauthors'] = coauthors

        if 'history' in query_dict['profile']['content']:
            tmp_dict = query_dict['profile']['content']['history'][0]
            if 'position' in tmp_dict:
                or_keyword_dict['position'] = tmp_dict['position']
            if 'institution' in tmp_dict:
                if 'domain' in tmp_dict['institution']:
                    or_keyword_dict['email_suffix'] = tmp_dict['institution']['domain']
                if 'name' in tmp_dict['institution']:
                    or_keyword_dict['organization'] = tmp_dict['institution']['name']

        or_keyword_list.append(or_keyword_dict)

    return or_keyword_list

# def generate_keyword_list(resp_gs_prop):
#     resp_gs = resp_gs_prop['resp_gs']
#     keyword_list = resp_gs
#     return keyword_list
class Scholar78kSearch():
    def __init__(self):
        self.get_78kdata()
        self.simple = False
        self.verbose = False
        self.print_true = True

    def get_78kdata(self, source='gself.drive'):
        # path_name = 'gs_scholars_all.npy'
        path_name = 'gs_wo_papers.npy'
        if source == 'gself.drive':
            import gdown
            if not os.path.exists('source'):
                os.mkdir('source')
            if not os.path.exists(f'source/{path_name}'):
                gdown.download(
                    'https://self.drive.google.com/uc?id=1eEKhUQyfCNl-wt9yLwEEQN8QSnlbmGtz',
                    f'source/{path_name}'
                )
        self.df = pd.DataFrame.from_records(np.load(f'source/{path_name}', allow_pickle=True))
        self.df.rename(columns={'co_authors': 'coauthors'}, inplace=True)
        # NOTE: rename, domain_tags
    
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
        if 'gscholar' in query_dict['profile']['content']['gscholar'] and 'user=' in query_dict['profile']['content']['gscholar']:
            gs_sid = query_dict['profile']['content']['gscholar'].split('user=', 1)[1][:12]
            return self.search_gsid(gs_sid)
        position, school = None, None
        if 'position' in query_dict['profile']['content']['history'][0]:
            position = query_dict['profile']['content']['history'][0]['position']
        if ('institution' in query_dict['profile']['content']['history'][0] and 
            'name' in query_dict['profile']['content']['history'][0]['institution']):
            school = query_dict['profile']['content']['history'][0]['institution']['name']
        url_item.append('authsearch')
        url_item.append(self._authsearch.format(requests.utils.quote(name)))

        return url_item

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
        return [scholar_dict]
        
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
        if 'user=' in url:
            gs_sid = url.split('user=', 1)[1][:12]
        else:
            gs_sid = None
        Researcher['gs_sid'] = gs_sid
        Researcher["coauthors"] = Co_authors
        Researcher["citation_table"] = [Citations_table[0], Citations_table[2]]
        Researcher["cites"] = {"years":years, "cites":cites}
        nameList = driver.find_elements(By.ID, "gsc_prf_in")
        if (len(nameList) != 1):
            return None
        Researcher["name"] = nameList[0].text
        infoList = driver.find_elements(By.CLASS_NAME, 'gsc_prf_il')
        Researcher['organization'] = infoList[0].get_attribute('textContent')
        Researcher['domain_labels'] = [i.get_attribute('textContent') for i in infoList[2].find_elements(By.CLASS_NAME, 'gsc_prf_inta')]
        if not simple:
            button = driver.find_elements(By.CLASS_NAME, 'gs_btnPD')
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

    def search_name(self, name: Union[str, list], query_dict, wo_full=True, simple=True):
        if type(name) is list:
            name_list = [name[0], name[-1]]
            name = f'{name[0]} {name[-1]}' 
        elif type(name) is str:
            name_list = name.split(' ')
        else:
            raise TypeError('Argument "name" passed to ScholarGsSearch.search_name has the wrong type.')
        # first try (name email_suffix position organization) as url
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
        
        # second try (name email_suffix)
        if 'email_suffix' in keyword_list:
            url_fragment_new = url_fragment + keyword_list['email_suffix'] + ' '
        # print(url_fragment_new)
        url = self._authsearch.format(url_fragment_new)
        # print(url)
        # print(keyword_list)
        self.driver.get(url)
        time.sleep(5)
        scholar_list = self._search_name_helper(self.driver, name_list)
        # return scholar_list
        if len(scholar_list) > 0:
            if wo_full:
                return scholar_list
            else:
                return self._search_name_list_expand(scholar_list, simple=simple)
        
        # finally,
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
                    domain_labels[idx] = domain.get_attribute('textContent').strip()

                # continue processing
                if 'user=' in url:
                    gs_sid = url.split('user=', 1)[1][:12]
                else:
                    gs_sid = None
                # print(email_str)
                # return [scholar_webdriver]
                # sys.exit(1)
                match = re.search(r'[\w-]+\.[\w.-]+', email_str)
                email_str = match.group(0)

                useful_info_ext_list.append({
                    'name': name,
                    'pos_org': pos_org,
                    'email': email_str,
                    'cite': [int(s) for s in cite.split() if s.isdigit()][0],
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
                new_scholar_list.append(scholar_dict)
                time.sleep(5)
        return new_scholar_list


    def _deal_with_simple(self, gs_dict):
        pass
    