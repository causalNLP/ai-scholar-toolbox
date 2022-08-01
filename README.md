# ai-scholar-toolbox

The python package provides an efficient way to get statistics of a scholar on Google Scholar given academic information of the scholar.

## Environment
Create an environment with the following commands:
```bash
virtualenv venv -p python3
source venv/bin/activate
pip install -r requirements.txt
```

## Download Browser Binary and Browser Driver
By default, our package uses Chromium binary file. Please take care the compatibility between the binary file and the browser driver. Also, if your OS is not linux based or you install the browser in a directory other than default directory, please refer to [Selenium Chrome requirements](https://github.com/SeleniumHQ/selenium/wiki/ChromeDriver/01fde32d0ed245141e24151f83b7c2db31d596a4#requirements) when instantiating the browser driver.

Download:
- [Download Chrome browser driver](https://sites.google.com/a/chromium.org/chromedriver/downloads)

Install:
- Linux
  
  ```bash
  sudo apt update
  sudo apt upgrade
  wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
  sudo apt install ./google-chrome-stable_current_amd64.deb
  ```
## Get Started in ai-scholar-toolbox

1. Instantiate a `ScholarSearch` object. This will download 78k dataset to the local machine automatically.
   ```python
   from ScholarSearch import ScholarSearch
   scholar_search = ScholarSearch()
   ```

2. Set attributes for the class:
   ```python
   # set the similarity ratio of comparing two strings when searching on Google Scholar webpage. If not given, default is 0.8.
   scholar_search.similarity_ratio = 0.8
   # set the path of browser driver.
   scholar_search.driver_path = '../../chromedriver'
   # required: setup
   scholar_search.setup()
   ```

   Optional: In case that you want to get responses of a list of scholars, the class method `get_profiles()` is implemented for you to load (could be multiple) json data files.
   ```python
   # optional
   scholar_search.get_profiles(['../review_data/area_chair_id_to_profile.json', '../review_data/reviewer_id_to_profile.json'])
   ```

3. Search candidate scholars by matching a specific query:
   
    If you want to input the information of a scholar on OpenReview and get related google scholar information, you can pass in a python **dictionary** with necessary features based on the OpenReview scholar profile page (for instance, from [Zhijing's OpenReview profile](https://openreview.net/profile?id=~Zhijing_Jin1)). Note that filling in more information as recommended below will get a better search result. **TODO: change the dict to be of a certain person.**
    
   ```python
   # keys that are required:
   # scholar_info_dict['content']['gscholar']: the link to Google Scholar profile in the OpenReview webpage. If cannot be found, you can either choose not to include it or pass in an empty string.
   # scholar_info_dict['content']['history']: the most updated history of the scholar in the OpenReview webpage. Previous history is not needed.
   # scholar_info_dict['content']['relations']: all relations that the scholar list in the OpenReview webpage. We recommend to list all the relations here. Only name is needed.
   # scholar_info_dict['content']['expertise']: all keywords that the scholar label their academic research field. We recommend to list all the expertise keywords here. Only keyword is needed.

   # Most recommended:
   scholar_info_dict = {
      "profile": {
          "id": "~Zhijing_Jin1", # most important information to use
          "content": {
              "gscholar": "https://scholar.google.com/citations?user=RkI8h-wAAAAJ",
              "history": [ # second most important information to use
                  {
                      "position": "PhD student",
                      "institution": {
                          "domain": "mpg.de",
                          "name": "Max-Planck Institute"
                      }
                  }
              ],
              "relations": [
                  {
                      "name": "Bernhard Schoelkopf"
                  },
                  {
                      "name": "Rada Mihalcea"
                  },
                  {
                      "name": "Mrinmaya Sachan"
                  },
                  {
                      "name": "Ryan Cotterell"
                  }
              ],
              "expertise": [
                  {
                      "keywords": [
                        "causal inference"
                      ]
                  },
                  {
                      "keywords": [
                        "computational social science"
                      ]
                  },
                  {
                      "keywords": [
                        "social good"
                      ]
                  },
                  {
                      "keywords": [
                        "natural language processing"
                      ]
                  }
              ]
          }
      }
   }

   # Minimum required but least recommended:
   scholar_info_dict = {
      "profile": {
          "id": "~Zhijing_Jin1",
          "content": {}
      }
   }
   ```

   Then, you can pass the dictionary to the method `get_scholar()` to get possible candidates.
   ```python
   # query: python dictionary that you just generated.
   resp = scholar_search.get_scholar(query=scholar_info_dict, simple=True, top_n=3, print_true=True)
   resp
   ```

   Alternatively, if you just want to input the name of a scholar and get possible google scholar candidates, you can pass the name as a string directly to the function as the following:
   ```python
   # query: python str, the name of the scholar.
   resp = scholar_search.get_scholar(query='Zhijing Jin', simple=True, top_n=3, print_true=True)
   resp
   ```

## Search Algorithms
The algorithm can be explained as follows if the input query is a python dictionary:
```python
def get_candidates(openreview_dict, top_n_related):
  if gs_sid in openreview_dict:
    if gs_sid in 78k_scholar:
      return dict(78k_scholar.loc[78k_scholar[‘gs_sid’]==gs_sid])
    else:
      response = search_directly_on_google_scholar_by_gssid(gs_sid)
      return response
  else:
      name, email_suffix, position, organization, relations = extract_name_from_openreview_dict(openreview_dict)
      response_78k = search_scholar_on_78k(name) 
      response_gs = search_scholar_on_google_scholar(name, email_suffix, position, organization, relations)
      response = select_final_candidates(response_78k, response_gs, top_n_related = top_n_related)
      return Response

```

## Statistics Summary
Our 78k dataset has 78,066 AI scholars in total. Please check our [78k AI scholar dataset](https://github.com/causalNLP) for more details.

Given all the chairs and reviewers in OpenReview (664 in total), our package achieves 93.02% precision, 85.11% recall, and 88.89% F1-score on a random subset of 50 scholars that don't have `gs_sid` included in the input dict.

## FAQ
**TODO: add content**

## Support
If you have any questions, bug reports, or feature requests regarding either the codebase or the models released in the projects section, please don't hesitate to post on our [Github Issues page](https://github.com/causalNLP/ai-scholar-toolbox/issues).

## License
The package is licensed under the MIT license.
**TODO: check licenses**