import pandas as pd
import numpy as np
import random
import re
from tensorflow import logging


def check_stopwords(text, stopwords):
    for word in stopwords:
        if word in text:
            return text
        return None


def text_cleaninig(text):
    stopwords = " [ ] { } ( ) _ - ! @ # $ % ^ * + = < > ? , . / |"
    for word in stopwords:
        text = text.replace(word,' ')
    return text.upper()


class Dataset():
    def __init__(self, df=None, datapath='', param=None, deterministic=True, train_rate=0.8):
        if df is None:
            self.df = pd.read_csv(datapath, sep='\u1234', index_col='Unnamed: 0', nrows=100000)
        else:
            self.df = df
        self.param = param
        self.deterministic = deterministic

        logging.info('Preprocessing started')

        self.vocab = None
        self.proc_df = self._prerpocess(self.df)
        train_size = int(train_rate * len(self.proc_df))
        self.train_df = self.proc_df.iloc[:train_size].copy()
        self.test_df = self.proc_df.iloc[train_size:].copy()

        logging.info('Preprocessing done')
        self.get_num_examples = len(self.proc_df)
        self.iterator = self._iterate()

    def _build_vocab(self, proc_df):
        char_list = ''.join(proc_df['proc_prdnm'].tolist())
        char_list = list(char_list)
        vocab = pd.Series(char_list).value_counts()
        vocab = vocab.reset_index().reset_index().set_index('index')
        vocab.info()
        print(vocab.head())
        return vocab

    def _entity_tag(self, prd_nm, brand):
        brand_list = brand.split()
        tag = '0' * self.param['vec_length']

        for brand in brand_list:
            index_list = [m.start() for m in re.finditer(brand, prd_nm)]
            if len(index_list) == 0:
                continue

            for index in index_list:
                tag = tag[:index] + tag[index].replace('0', '1') + tag[index+1:]
                tag = tag[:index+1] + tag[index+1:index+len(brand)].replace('0', '2') + tag[index+len(brand):]

        return tag

    def _mark_padding(self, prd_nm):
        tag = '0' * self.param['vec_length']
        length = len(prd_nm)
        tag = tag[:length].replace('0','1') + tag[length:]
        return tag

    def _add_padding(self, l):
        size = len(l)
        limit = self.param['vec_length']
        if size > limit:
            print('size is big:', size)
        return l[:limit] + [0]*(self.param['vec_length'] - size)

    def _prerpocess(self, df):
        stopwords = ['없음', '참조', '상세', '상품', '설명']
        df['check_stopwords'] = df['ATTR_VALUE_NM'].apply(check_stopwords, args=(stopwords,))
        df['proc_prdnm'] = df['PRD_NM'].apply(text_cleaninig)
        df['proc_attr'] = df['ATTR_VALUE_NM'].apply(text_cleaninig)
        self.vocab = self._build_vocab(df)

        sub = df[df.check_stopwords.isnull()][['proc_prdnm', 'proc_attr']]
        sub['label'] = sub.apply(lambda row: self._entity_tag(row['proc_prdnm'], row['proc_attr']), axis=1)
        sub['x'] = sub['proc_prdnm'].apply(lambda x: self._add_padding([self.vocab.loc[char]['level_0'] for char in list(x)]))
        sub['y'] = sub['label'].apply(lambda x: list(map(int, list(x))))
        sub['w'] = sub['proc_prdnm'].apply(lambda x: list(map(int, list(self._mark_padding(x)))))

        return sub.copy()

    def row2input(self, index, stride, train=True):

        if train:
            row = self.train_df.iloc[index:index + stride]
        else:
            row = self.test_df.iloc[index:index + stride]

        x = row['x']
        x = np.array(x.tolist())

        y = row['y']
        y = np.array(y.tolist())

        w = row['w']
        w = np.array(w.tolist())

        if (x.shape[0] != stride) or (x.shape[1] != 128):
            print(index, stride, x.shape)

        return x, y, w, row

    def _iterate(self, train=True):
        batchsize = self.param['batch_size']
        index = 0
        while index < len(self.train_df):
            x, y, w, row = self.row2input(index, batchsize, train)
            index = index + batchsize

            yield x, y, w

    def init_iter(self):
        self.iterator = self._iterate()

    def unit_test(self):
        for i in range(3):
            a_batch_data = next(self.iterator)
            x, y, w = a_batch_data
            print(i, x.shape, y.shape, w.shape)


if __name__ == '__main__':
    path = 'data/test_data_set.csv'
    param = {'enc_dim':50, 'batch_size':100, 'vec_length':128}
    dataset = Dataset(datapath=path, param=param)
    dataset.unit_test()
