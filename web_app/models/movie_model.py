from web_app import db


class Credit(db.Model):
    __tablename__ = 'credits'
    movie_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    cast = db.Column(db.Text)
    crew = db.Column(db.Text)


class Genre(db.Model):
    __tablename__ = 'genres'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))


movies_genres = db.Table('movies_genres',
    db.Column('movie_id', db.Integer, db.ForeignKey('movies.id'), primary_key=True),
    db.Column('genre_id', db.Integer, db.ForeignKey('genres.id'), primary_key=True)
)


class Company(db.Model):
    __tablename__ = 'companies'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))


movies_companies = db.Table(
    'movies_companies',
    db.Column('movie_id', db.Integer, db.ForeignKey('movies.id'), primary_key=True),
    db.Column('company_id', db.Integer, db.ForeignKey('companies.id'), primary_key=True)
)


class Country(db.Model):
    __tablename__ = 'countries'
    abbr = db.Column(db.String(255), primary_key=True)
    name = db.Column(db.String(255))


movies_countries = db.Table(
    'movies_countries',
    db.Column('movie_id', db.Integer, db.ForeignKey('movies.id'), primary_key=True),
    db.Column('country_abbr', db.String(255), db.ForeignKey('countries.abbr'), primary_key=True)
)


# class MovieComment(db.Model):
#     __tablename__ = 'movie_comments'
#
#
# class UserRateMovie(db.Model):
#     __tablename__ = 'user_rate_movies'


class MoviePoster(db.Model):
    __tablename__ = 'movie_posters'
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.id'), primary_key=True)
    poster = db.Column(db.Binary)


class Movie(db.Model):
    __tablename__ = 'movies'
    id = db.Column(db.Integer, primary_key=True)
    budget = db.Column(db.String(255))
    genres = db.relationship('Genre', secondary=movies_genres, lazy='dynamic',
                             backref=db.backref('movies', lazy='dynamic'))
    homepage = db.Column(db.String(255))
    keywords = db.Column(db.Text)
    original_language = db.Column(db.String(255))
    original_title = db.Column(db.String(255))
    overview = db.Column(db.Text)
    popularity = db.Column(db.Float)
    production_companies = db.relationship('Company', secondary=movies_companies, lazy='dynamic',
                                           backref=db.backref('movies', lazy='dynamic'))
    production_countries = db.relationship('Country', secondary=movies_countries, lazy='dynamic',
                                           backref=db.backref('movies', lazy='dynamic'))
    release_date = db.Column(db.DateTime)
    revenue = db.Column(db.BigInteger)
    runtime = db.Column(db.Integer)
    spoken_languages = db.Column(db.Text)
    status = db.Column(db.String(255))
    tagline = db.Column(db.String(255))
    title = db.Column(db.String(255))
    vote_average = db.Column(db.Float)
    vote_count = db.Column(db.BigInteger)