import pandas as pd
import numpy as np
import pickle
import json
import typing
from typing import List, Union
import os
import re
import time
import sys
import requests
from difflib import SequenceMatcher
from bs4 import BeautifulSoup
from Scholar78kSearch import Scholar78kSearch
from ScholarGsSearch import ScholarGsSearch



class ScholarSearch():
    def __init__(self):
        # self.get_profiles(['review_data/area_chair_id_to_profile.json', 'review_data/reviewer_id_to_profile.json'])
        # self.get_profiles(None)
        self.search_78k = Scholar78kSearch()
        self.search_gs = ScholarGsSearch()
        self.find_list = []

        # attributes
        self.similarity_ratio = 0.8

    def reset(self):
        pass

    def get_profiles(self, filepath_list: List[str] = None) -> None:
        """In case that you want to get responses of a list of scholars, 
        the method is implemented for you to load (could be multiple) json data files.
        If using this method, please

        Parameters
        ----------
        filepath_list: list of json data filepaths to load.

        """
        if filepath_list is None:
            return
        # set of json data dicts
        self.profile = {}
        for filepath in filepath_list:
            with open(filepath) as file:
                profile = json.load(file)
                self.profile.update(profile)
        # number of unique json data dicts in total
        print(f'Number of unique json data dicts in total: {len(self.profile)}')

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
        dict = None
        real_name = True
        # OpenReview id
        if ' ' not in name and name[0] == '~':
            # search over chair id
            if name in self.profile:
                dict = self.profile[name]
            # crawl http api response
            if dict is not None and not from_dict:
                # name
                real_name = False
                resp = self.search_dict(dict, simple=simple, top_n=top_n)
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
            resp = self.search_78k.search_name(name, query_dict)
            # TODO: integrate resp_gs with resp
            if from_dict:
                print('Not find by gs_sid, search from_dict')
                or_resp = None
                resp_gs = self.search_gs.search_name(name, query_dict, wo_full=wo_full, top_n=top_n, simple=simple)
                resp = self.select_final_cands(resp, or_resp, top_n, query_dict=query_dict, resp_gs_prop={'wo_full': wo_full, 'resp_gs': resp_gs})
            else:
                print('Not found by gs_sid, search without from_dict')
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
            # if there are one candidate from google scholar pages, we throw out resp from 78k data.
            if len(resp_gs) == 1:
                resp = []
            # iterate over resp_gs
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
                    if resp_gs_full_item is not None:
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
                    for cand_domain_tag in cand['domain_labels']:
                        cnt_all += 1
                        for or_domain_tag in or_scholar['domain_labels']:
                            if get_str_similarity(cand_domain_tag, or_domain_tag) >= self.similarity_ratio:
                                cnt_true[idx_or_scholar] += 1
                
                
                # relations
                cnt_all_rel = 0
                # print(cand)
                if cand['coauthors'] is not None:
                    for cand_coauth in cand['coauthors']:
                        cnt_all_rel += 1
                        for or_coauth in or_scholar['coauthors']:
                            if get_str_similarity(or_coauth, cand_coauth[1]) >= self.similarity_ratio:
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
        
        # select final candidate
        final_idx = []
        for rank_idx in rank:
            if rank[rank_idx][0] == 1:
                final_idx.append(rank_idx)
        
        # TODO: or we can set weights to (relations, domain_tags) to rank the scholar candidates
        if len(final_idx) < top_n:
            domain_tag_rank = []
            relation_rank = []
            for rank_idx in sorted(rank.keys()):
                # print(rank_idx)
                domain_tag_rank.append(rank[rank_idx][1])
                relation_rank.append(rank[rank_idx][2])
            # print(domain_tag_rank, relation_rank)
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
            if len(final_idx) == 0 and len(rank.keys()) > 0:
                    for rank_idx in sorted(rank.keys()):
                        if len(final_idx) >= top_n:
                            break
                        else:
                            final_idx.append(rank_idx)
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
            tmp_gs_sid = query_dict['profile']['content']['gscholar'].split('user=', 1)[1]
            if len(tmp_gs_sid) >= 12:
                gs_sid = tmp_gs_sid[:12]
                name_df = self.search_78k.df.loc[self.search_78k.df['gs_sid'] == gs_sid].copy()
                if name_df.shape[0] != 0:
                    print(f'[Info] Found a scholar using 78k gs_sid')
                    return self.search_78k._deal_with_simple(name_df)
                else:
                    print(f'[Info] Found a scholar using query dict gs_sid')
                    self.find_list.append(query_dict)
                    resp = self.search_gs.search_gsid(gs_sid, simple=simple)
                    if len(resp) > 0:
                        return resp
                    
        
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
                        key = key.strip().lower()           
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
        if 'relations' in query_dict['profile']['content'] and len(query_dict['profile']['content']['relations']) > 0:
            for relation in query_dict['profile']['content']['relations']:
                coauthors.append(relation['name'])
        or_keyword_dict['coauthors'] = coauthors

        if 'history' in query_dict['profile']['content'] and len(query_dict['profile']['content']['history']) > 0:
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

def get_str_similarity(a: str, b: str):
    return SequenceMatcher(None, a, b).ratio()


