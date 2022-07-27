# UAI 2022 Review data

## Dataset description

### `{reviewer/area_chair}_id_to_profile.json`
These two files contain all reviewer / area chair profiles which are available online. Please note that these two files contain identity information, please keep it confidential. Other files use tokens to de-identify reviewers and meta reviewers.

```json
{
    "openreview_id":{
        "profile": {"profile"},
        "papers": [
            {"paper1"},
            {"paper2"},
            {"..."}
        ]
    }
}
```
### `review_scores_{before/after}_rebuttal.csv`
These two files decribe the change of scores during rebuttal. The content is self-explained by file names
```csv
Reviewer ID,Paper ID,Originality,Significance,Correctness,Experiments,Reproducibility,Clarity,Overall
```
### `forum_id_to_notes.json`
This file contains **all** reviews / meta reviews / discussions for each paper. The `forum_id` is the unique id for each paper. Accepted paper websites can be accessed via https://openreview.net/forum?id=`forum_id`


```json
{
    "forum_id":{
        [
            {"decision"},
            {"meta review"}.
            {"discussions"},
            {"reviews"},
            {"other messages"}
        ]
    }
}
```