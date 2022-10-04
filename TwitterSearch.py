import re
import time
from typing import Union
from collections import defaultdict
from selenium import webdriver
from selenium.webdriver.chromium.webdriver import ChromiumDriver
from selenium.webdriver.common.by import By
from ScholarGsSearch import GoogleSearch
from bs4 import BeautifulSoup

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

    def search_scholar(self, str_type: str, term: str):
        """
        NOTE: now the only allowed str_type is name
        """
        if str_type == 'name':
            result = self._search_name_helper(term)
            return self.filter_result(result, term, web_source='google')
        else:
            raise NotImplementedError

    def _search_name_helper(self, term: str):
        url = self._urlsearch.format(term)
        self.driver.get(url)

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
        print(result_list)
        time.sleep(5)

    def filter_result(self, result_list, term, web_source):
        """
        web_source: google, twitter
        """
        if web_source == 'google':
            self.twitter_id_dict = defaultdict(int)
            for result in result_list:
                if 'https://twitter.com/' in result['href']:
                    self.twitter_id_dict[re.findall('https://twitter.com/([^\/]+)')[0]] += 1
        
        # goal 1: for 78k scholars, get their twitter accounts
        # known information: scholar's name, 

        # step 1: get a candidate list of twitter account id (name "twitter"; )
        # step 2: 


        # goal 2: for arbitrary scholars, get their twitter accounts

    def get_scholar_twitter(self, str_type: str, term: str, only_one=True):
        """
        Final function that search a scholar's twitter account
        """

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