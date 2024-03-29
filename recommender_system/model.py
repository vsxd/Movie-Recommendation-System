import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
from ast import literal_eval
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from surprise import Reader, Dataset, SVD


class DemographicFiltering:
    def __init__(self, df, quantile_num=0.9):
        if not isinstance(df, pd.DataFrame):
            raise TypeError('DemographicFiltering need Pandas.DataFrame objects: df')
        self.df = df
        self._vote_average_mean = df['vote_average'].mean()  # vote_average的平均值
        self._vote_count_quantile = df['vote_count'].quantile(quantile_num)  # vote_count的分位数
        self._q_movies = None
        self._pop_movies = None

    def _weighted_rating(self, elem):
        m = self._vote_count_quantile
        C = self._vote_average_mean
        v = elem['vote_count']
        R = elem['vote_average']
        # 基于IMDB的Weighted Rating计算公式
        return (v / (v + m) * R) + (m / (m + v) * C)

    def calculate(self):
        q_movies = self.df[['id', 'title', 'vote_count', 'vote_average', 'popularity']].copy() \
            .loc[self.df['vote_count'] >= self._vote_count_quantile]
        q_movies.shape  # log
        # 定义一个新feature score，值为每行计算的weighted rating
        q_movies['score'] = q_movies.apply(self._weighted_rating, axis=1)
        # 对score列从大到小排序
        self._q_movies = q_movies.sort_values('score', ascending=False)
        self._pop_movies = self.df.sort_values('popularity', ascending=False)

    def get_results(self):
        """
        :return: tuple(rank1: PandasArray, rank2: PandasArray)
        """
        return self._q_movies['id'].array, self._pop_movies['id'].array


class ContentBasedFiltering:
    def __init__(self, df, results_num=100):
        if not isinstance(df, pd.DataFrame):
            raise TypeError('ContentBasedFiltering need Pandas.DataFrame objects: df')
        self.df = df
        self._indices = pd.Series(self.df.index, index=self.df['id'])  # 构造反向映射
        self._results_num = results_num
        self._sim_matrix1 = None
        self._sim_matrix2 = None

    def _get_recommendations(self, movie_id, cosine_sim):
        idx = self._indices[movie_id]  # 根据movie id获得矩阵中的行index

        # 从cosine_sim矩阵的idx行 构造一个pair:(index,sim_score), 放在list中。
        sim_scores = list(enumerate(cosine_sim[idx]))

        # 根据pair中的sim_score从大到小排序
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        if self._results_num is not None:
            sim_scores = sim_scores[1:self._results_num + 1]  # 第一个是自身，得到前results_num个similarity score最高的
        movie_indices = [i[0] for i in sim_scores]
        return self.df['id'].iloc[movie_indices].array  # 根据index返回id的PandasArray / 或者.values返回ndarray

    @classmethod
    def __get_director(cls, x):
        # 通过crew list得到导演的名字
        for i in x:
            if i['job'] == 'Director':
                return i['name']
        return np.nan

    @classmethod
    def __get_list(cls, x, max_names=5):
        # 将dict组成的list变为单纯的字符串list形式
        if isinstance(x, list):
            names = [i['name'] for i in x]
            # 限制返回的名字数量
            if len(names) > max_names:
                names = names[:max_names]
            return names
        # missing or malformed data
        return []

    @classmethod
    def _clean_data(cls, x):
        if isinstance(x, list):
            return [str.lower(i.replace(" ", "")) for i in x]  # lowercase、移除空格
        else:
            if isinstance(x, str):  # director列 lowercase、移除空格
                return str.lower(x.replace(" ", ""))
            else:
                return ''

    @classmethod
    def _create_soup(cls, x):
        # create "metadata soup"
        return ' '.join(x['keywords']) + ' ' + ' '.join(x['cast']) + ' ' + x['director'] + ' ' + ' '.join(x['genres'])

    def _calculate_b(self):
        df2 = self.df.copy()
        features = ['cast', 'crew', 'keywords']
        for feature in features:  # 将str转换为list(dict())
            df2[feature] = df2[feature].apply(literal_eval)

        # 建立director feature
        df2['director'] = df2['crew'].apply(self.__get_director)

        features = ['cast', 'keywords']  # genres列在从db导入时已经格式化为list形式
        for feature in features:
            df2[feature] = df2[feature].apply(self.__get_list)

        # 对features应用clean_data().
        features = ['cast', 'keywords', 'director', 'genres']
        for feature in features:
            df2[feature] = df2[feature].apply(self._clean_data)

        df2['soup'] = df2.apply(self._create_soup, axis=1)

        count = CountVectorizer(stop_words='english')
        count_matrix = count.fit_transform(df2['soup'])

        cosine_sim2 = cosine_similarity(count_matrix, count_matrix)
        return cosine_sim2

    def _calculate_a(self):
        # 初始化TfidfVectorizer对象，stop_words会移除英文中冠词介词之类的词
        tfidf = TfidfVectorizer(stop_words='english')

        # 将NaN替换为空字符串
        self.df['overview'] = self.df['overview'].fillna('')

        # 构造TF-IDF矩阵
        tfidf_matrix = tfidf.fit_transform(self.df['overview'])
        tfidf_matrix.shape

        # 计算tfidf矩阵与自身的similarity矩阵
        cosine_sim = linear_kernel(tfidf_matrix, tfidf_matrix)
        cosine_sim.shape
        return cosine_sim

    def calculate(self):
        """
        :return: 'Done' or 'Except occurred'
        """
        try:
            self._sim_matrix1 = self._calculate_a()
            self._sim_matrix2 = self._calculate_b()
            return 'Done'
        except:
            return 'Except occurred'

    def get_results(self, movie_id):
        """
        :param movie_id: int
        :return: tuple(recomm1: PandasArray, recomm2: PandasArray)
        """
        return (self._get_recommendations(movie_id, cosine_sim=self._sim_matrix1),
                self._get_recommendations(movie_id, cosine_sim=self._sim_matrix2))


class CollaborativeFiltering:
    def __init__(self, rating_df, user_df, movie_df, movie_sim_matrix=None):
        self._df = movie_df
        self._rating_df = rating_df
        self._movie_sim = movie_sim_matrix
        self._theta_m_u = np.zeros([movie_df.shape[0], user_df.shape[0]], dtype=np.float32)
        # self._x_m_n = np.zeros([df.shape[0], feature_n], dtype=np.float32)
        self._movie_indices = pd.Series(movie_df.index, index=movie_df['id'])
        self._user_indices = pd.Series(user_df.index, index=user_df['id'])  # 构造反向映射
        self._algo = SVD()

    def _get_sim_user(self, user_id, top_n=10):
        pass

    def _get_sim_movie(self, movie_id, top_n=10):
        pass

    def calculate(self):
        # for item in self._rating_df.to_numpy():
        #     self._theta_m_u[self._movie_indices[int(item[0])], self._user_indices[int(item[1])]] = item[2]

        # cosine_similarity(self._theta_m_u.T, self._theta_m_u.T)
        # cosine_similarity(self._theta_m_u, self._theta_m_u)
        reader = Reader()
        data = Dataset.load_from_df(self._rating_df[['user_id', 'movie_id', 'score']], reader)
        trainset = data.build_full_trainset()
        self._algo.fit(trainset)

    def get_results(self, user_id, movie_id):
        return self._algo.predict(user_id, movie_id).est
