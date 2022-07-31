# ai-scholar-toolbox


## Statistics Summary

## Environment
Create an environment with the following commands:
```bash
virtualenv venv -p python3
source venv/bin/activate
pip install -r requirements.txt
```

## Download Browser Binary and Browser Driver


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
   ```

   Optional: In case that you want to get responses of a list of scholars, the class method `get_profiles()` is implemented for you to load (could be multiple) json data files.
   ```python
   # optional
   scholar_search.get_profiles(['review_data/area_chair_id_to_profile.json', 'review_data/reviewer_id_to_profile.json'])
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
   # simple: 
   resp = scholar_search.get_scholar(query=scholar_info_dict, simple=True, top_n=3, print_true=True)
   resp
   ```

   Alternatively, if you just want to input the name of a scholar and get possible google scholar candidates, you can pass the name as a string directly to the function as the following:
   ```python

   ```

## FAQ


## Support
If you have any questions, bug reports, or feature requests regarding either the codebase or the models released in the projects section, please don't hesitate to post on our [Github Issues page](https://github.com/facebookresearch/metaseq/issues).

## License
The package is licensed under the MIT license.
`todo: check licenses`