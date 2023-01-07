import re
import time
from typing import Union
from collections import defaultdict
from selenium import webdriver
from selenium.webdriver.chromium.webdriver import ChromiumDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.errorhandler import WebDriverException
from ScholarSearch import ScholarSearch
from ScholarGsSearch import GoogleSearch
from bs4 import BeautifulSoup
from utils import get_str_similarity

url_search_dict = {
    'google': 'https://www.google.com/search?q={0}'
}


def get_search_result(**kwargs):
    return kwargs


class TwitterSearch(GoogleSearch):
    """Class that handling searching on Google search bar using REST API."""

    def __init__(self, driver_path):
        super().__init__(driver_path)
        self._urlsearch = url_search_dict['google']
        self.print_true = True #NOTE: should be set by users
        # initialize scholar_search object
        self.scholar_search = ScholarSearch()
        self.scholar_search.setup()

    def search_scholar(self, str_type: str, term: str):
        """
        NOTE: now the only allowed str_type is name
        """
        if str_type == 'name':
            scholar_search_result = self.scholar_search.get_scholar(query=term, simple=True, top_n=1, print_true=True)
            branch_type = None
            if len(scholar_search_result) == 0:
                # directly search
                url_fragment = self._urlsearch.format(f'{term} "twitter"')
                result = self._search_google_helper(url_fragment)
                twitter_ids = self.filter_result(result, term, web_source='google')
                branch_type = 'directly search'
            else:
                twitter_ids = None
                # try directly get twitter account through homepage
                if 'homepage_url' in scholar_search_result[0] and scholar_search_result[0]['homepage_url'] is not None:
                    twitter_ids = self._search_twitter_from_homepage(scholar_search_result[0]['homepage_url'], name=term, name_from_gs=scholar_search_result[0]["name"])
                if twitter_ids is not None:
                    branch_type = 'homepage'

                # then try (google_name email_suffix "twitter")
                if "email_info" in scholar_search_result[0] and scholar_search_result[0]["email_info"] != '' and twitter_ids is None:
                    url_fragment = self._urlsearch.format(f'{scholar_search_result[0]["name"]} {scholar_search_result[0]["email_info"]} "twitter"')
                    result = self._search_google_helper(url_fragment)
                    twitter_ids = self.filter_result(result, term, web_source='google')
                if twitter_ids is not None:
                    branch_type = 'name + email'

                # then try (google_name organization "twitter")
                if "organization" in scholar_search_result[0] and scholar_search_result[0]["organization"] != '' and twitter_ids is None:
                    url_fragment = self._urlsearch.format(f'{scholar_search_result[0]["name"]} {scholar_search_result[0]["organization"]} "twitter"')
                    result = self._search_google_helper(url_fragment)
                    twitter_ids = self.filter_result(result, term, web_source='google')
                if twitter_ids is not None:
                    branch_type = 'name + organization'

                # then try (google_name "twitter")
                if twitter_ids is None:
                    url_fragment = self._urlsearch.format(f'{scholar_search_result[0]["name"]} "twitter"')
                    result = self._search_google_helper(url_fragment)
                    twitter_ids = self.filter_result(result, term, web_source='google')
                if twitter_ids is not None:
                    branch_type = 'name'


            if self.print_true:
                print(f'[INFO] branch_type: {branch_type}')
                print(f'[INFO] twitter_ids: {twitter_ids}')

            if twitter_ids is None or len(twitter_ids) == 0:
                return None
            elif type(twitter_ids) == dict:
                twitter_ids_list = list(twitter_ids.keys())
                highest_occurrence = twitter_ids[twitter_ids_list[0]]
                candidate_list = []
                for item in twitter_ids:
                    if item[1] == highest_occurrence:
                        if self._rank_by_similarity(item[0], term, scholar_search_result[0]["name"]) >= 0.15:
                            candidate_list.append(item[0])
                if len(candidate_list) > 0:
                    return self._rank_by_similarity(candidate_list, term, scholar_search_result[0]['name'])[0]
                return None
            else:
                return twitter_ids[0]

            # TODO: match profile images of google_scholar/homepage with twitter profile images
            # result = self._search_name_helper(term)
            # return self.filter_result(result, term, web_source='google')
        elif str_type == 'gs_url':
            raise NotImplementedError
        else:
            raise NotImplementedError

    def _rank_by_similarity(self, twitter_url_origin_list: Union[list, str], name: str=None, name_from_gs: str=None):
        # process name and name_from_gs
        if name is not None:
            name = re.sub('[0-9_\., ]', '', name.lower())
        if name_from_gs is not None:
            name_from_gs = re.sub('[0-9_\., ]', '', name_from_gs.lower())

        if type(twitter_url_origin_list) == list:
            
            # else
            twitter_url_list = [re.sub('[0-9_\., ]', '', item) for item in twitter_url_origin_list]
            twitter_url_map_dict = {re.sub('[0-9_\., ]', '', item): item for item in twitter_url_origin_list}
            # rank twitter_url_origin_list
            if name is not None and name_from_gs is not None:
                twitter_url_list = sorted(twitter_url_list, key=lambda x: max(get_str_similarity(x, name), get_str_similarity(x, name_from_gs)), reverse=True)
            elif name is not None:
                twitter_url_list = sorted(twitter_url_list, key=lambda x: get_str_similarity(x, name), reverse=True)
            elif name_from_gs is not None:
                twitter_url_list = sorted(twitter_url_list, key=lambda x: get_str_similarity(x, name_from_gs), reverse=True)
            else:
                # do not consider this branch at the moment
                pass
            twitter_url_origin_list = [twitter_url_map_dict[item] for item in twitter_url_list]
            return twitter_url_origin_list
        else:
            twitter_url_origin_str = twitter_url_origin_list
            twitter_url_str = re.sub('[0-9_\., ]', '', twitter_url_origin_str)
            rank = 0
            if name is not None and name_from_gs is not None:
                rank = max(get_str_similarity(twitter_url_str, name), get_str_similarity(twitter_url_origin_list, name_from_gs))
            elif name is not None:
                rank = get_str_similarity(twitter_url_str, name)
            elif name_from_gs is not None:
                rank = get_str_similarity(twitter_url_str, name_from_gs)
            
            return rank

    def _search_twitter_from_homepage(self, homepage_url: str, name: str=None, name_from_gs: str=None):
        # get content of scholar homepage using chromedriver
        try:
            self.driver.get(homepage_url)
        except WebDriverException as e:
            if self.print_true:
                print('[DEBUG] WebDriverException while getting homepage: %s' % homepage_url)
                print(e)
        time.sleep(3)

        page = self.driver.page_source
        soup = BeautifulSoup(page, "html.parser")
        twitter_url_origin_list = list(set([re.findall('twitter.com/([^\/?]+)', item['href'])[0]
            for item in soup.find_all(
                href=re.compile('twitter.com/([^\/?]+)'))]))
        print(soup.find_all(
                href=re.compile('twitter.com/([^\/?]+)')))
        # if there are no candidates for twitter account url, return None
        if len(twitter_url_origin_list) == 0:
            # return soup
            return None

        twitter_url_origin_list = self._rank_by_similarity(twitter_url_origin_list, name=name, name_from_gs=name_from_gs)

        if self.print_true:
            print(f'[DEBUG] Find a set of twitter ids on the provided homepage:\n{twitter_url_origin_list}')
        
        # only return the highest rank twitter account id
        return twitter_url_origin_list

    def _search_google_helper(self, google_url: str):
        self.driver.get(google_url)
        time.sleep(3)

        page = self.driver.page_source
        soup = BeautifulSoup(page, "html.parser")

        result_list = []
        result_block = soup.find_all('div', attrs={'class': 'g'})
        for result in result_block:
            # Find link, title, description
            link = result.find('a', href=True)
            title = result.find('h3')
            description_box = result.find(
                'div', {'style': '-webkit-line-clamp:2'})
            if link and title and description_box:
                result_list.append(get_search_result(
                    href=link['href'], title=title.text, description=description_box.text))
        if self.print_true:
            print(result_list)
        time.sleep(5)
        return result_list
        

    def filter_result(self, result_list, term, web_source):
        """
        web_source: google, twitter
        """
        # sort twitter ids by occurrence frequency
        if web_source == 'google':
            twitter_id_dict = defaultdict(int)
            for result in result_list:
                if 'twitter.com/' in result['href']:
                    twitter_id_dict[re.findall('twitter.com/([^\/?]+)', result['href'])[0]] += 1
        twitter_id_dict = dict(sorted(twitter_id_dict.items(), key=lambda item: item[1], reverse=True))
        # then, sort twitter ids by str similarity?
        # TODO
        # TODO: enter into twitter page to check profile information
        # Step 1: twitter profile vs google scholar profile
        # Step 2: twitter tweets: check whether google scholar domains are in twitter tweets
        # Step 3: twitter profile image (ask Yvonne about the performance)
        
        if len(twitter_id_dict) == 0:
            return None
        else:
            return twitter_id_dict
    
    def search_scholar_batch(self, name_list: list):
        self.result_list = []
        for name in name_list:
            self.result_list.append(self.search_scholar('name', name))
        return self.result_list

    def get_scholar_twitter(self, str_type: str, term: str, only_one=True):
        """
        Final function that search a scholar's twitter account
        # TODO
        """
        raise NotImplementedError
        result = self.search_scholar(str_type=str_type, term=term)

        # first, google web search: name "twitter", get a list of top results, and check whatever name matches exactly
        # if matches, then get the twitter account id, use tweepy API search of the id to get the user profile and do further check

        # if no matches, then search by name directly using Tweepy

        # if there are candidates, do type 1, 2, 3 check of the result
        #

        # '''
        #     The current code and the data is on the folder /cluster/project/sachan/zhiheng/twiteer at Euler server, because of the security reason, I save the twitter key as this structure, and use get_auth.py to load the key in the file. If you need more APIs, please contact me
        #     {
        #     "API_key" : "ilH6jnBJdh9HQdsufmygvUwMB",
        #     "API_secret_key" : "LqErCdWfdP6BWf3LH3Q0RrJAXHoFvmweBUNtI1WljJ2A8SMelW"
        #     }
        #     The current algorithm has the follow steps
        #     Step1: Find all twitter’s screen name by simply search the GS_name on twitter save_twitter_metainfo.py
        #     The problem now is that simply search the GS_name have a low recall rate, which is seen as the current bottleneck, about 52% of valid user loose in this step (see the below information)
        #     Step2: Use match_and_save.py to make a sketch match by the type 1, 2, 3 match and save those users tweets
        #     type 1: matched by personal website
        #     type 2: matched by keyword
        #     type3: matched by similar description with the information in GS
        #     Step3: Process the tweets (not important in current step)
        #     For the current 400 datapoint, there are 136 valid twitter accounts. I can match 20 of them by personal website, 36 of them by using type 1,2,3 match(with FN=20), and only 66 of them appeared in our search by users name (for example, if I simply search "Mohammad Moradi", I can not find the correspondent user moradideli by https://twitter.com/search?q=Mohammad%20Moradi&src=typed_query&f=user).
        #     8:45
        #     Here is some useful info about how a person annotator find the ground truth twitter user:
        #     8:46
        #     I followed the instruction in this doc by searching the name + Twitter in the Google first, and click top results to see if there is any match. If none, I will go search the name in Twitter and also browse through the top results. Sometimes I will also search their LinkedIn page to get their most up-to-date information. (the current institute in Google Scholar is not as accurate as their LinkedIn, and LinkedIn has a full history of where they worked. Moreover, they tend to put their photos in LinkedIn)
        # '''


# literature:

# https://direct.mit.edu/qss/article/1/2/771/96149/Large-scale-identification-and-characterization-of