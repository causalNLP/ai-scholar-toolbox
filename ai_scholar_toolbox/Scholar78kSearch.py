import pandas as pd
import os
import numpy as np
from typing import Union, List


class Scholar78kSearch():
    def __init__(self):
        self.get_78kdata()
        self.simple = False
        self.verbose = False
        self.print_true = True

    def get_78kdata(self, source='gdrive'):
        """Download and load the 78k dataset data.
        
        Parameters
        ----------
        source : default is 'gdrive'.
        """
        # path_name = 'gs_scholars_all.npy'
        path_name = 'gs_scholars_new.npy'
        if source == 'gdrive':
            import gdown
            if not os.path.exists('source'):
                os.mkdir('source')
            if not os.path.exists(f'source/{path_name}'):
                gdown.download(
                    'https://self.drive.google.com/uc?id=1NTvn_HiGX3Lr0FtTw5ot3UxcdeNLsv7h',
                    f'source/{path_name}'
                )
            self.df = pd.DataFrame.from_records(np.load(f'source/{path_name}', allow_pickle=True))
        else:
            raise NotImplementedError
    
    def search_name(self, name: Union[str, list], query_dict: dict = None) -> List[dict]:
        """Search scholar candidates given name in the 78k AI scholar dataset.
        
        Parameters
        ----------
        name : name of the scholar.
        query_dict : if this is given, the method will run <self._search_name_others_helper()>

        Returns
        -------
        df_row_list : a list of response dictionaries.
        
        """
        if type(name) is list:
            name_list = [name[0], name[-1]]
            name = f'{name[0]} {name[-1]}' 
        elif type(name) is str:
            name_list = name.split(' ')
        else:
            raise TypeError(f'Argument "name" passed to Scholar78kSearch.search_name has the wrong type.')
        df_row = self._search_name_only_helper(name, name_list)
        if df_row.shape[0] > 0 and query_dict is not None:
            df_row = self._search_name_others_helper(df_row, query_dict)
        if self.print_true:
            print(f'[Info] Found {df_row.shape[0]} scholars are in 78k data.')
            print(f'[Debug] Names: {df_row["name"]}')
        if self.verbose:
            print(df_row)
        return self._deal_with_simple(df_row)
        # return df_row

    def _deal_with_simple(self, df_row):
        if self.simple:
            df_row = df_row.loc[:, df_row.columns != 'papers']
        df_row = df_row.drop(['co_authors_all'], axis=1)
        return df_row.to_dict(orient='records')

    def _search_name_only_helper(self, name, name_list):
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

    def _search_name_others_helper(self, df_row, query_dict):
        # TODO: add a better filter more than by name
        return df_row