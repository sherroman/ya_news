import pytest
from news.models import Comment, News
from yanews import settings
from django.urls import reverse
from datetime import datetime, timedelta
from django.utils import timezone


@pytest.fixture
def news():
    return News.objects.create(title='Заголовок', text='Текст новости')


@pytest.fixture
def author(django_user_model):
    return django_user_model.objects.create(username='Автор')


@pytest.fixture
def url_home():
    return reverse('news:home')


@pytest.fixture
def url_detail(news):
    return reverse('news:detail', args=(news.id,))


@pytest.fixture
def all_news():
    today = datetime.today()
    all_news = [
        News(
            title=f'Новость {index}',
            text='Просто текст.',
            date=today - timedelta(days=index)
        )
        for index in range(settings.NEWS_COUNT_ON_HOME_PAGE + 1)
    ]
    return all_news


# Проверяем, что на главной странице отображается 10 новостей:
@pytest.mark.django_db
def test_news_count(all_news, client, url_home):
    News.objects.bulk_create(all_news)
    response = client.get(url_home)
    object_list = response.context['object_list']
    news_count = len(object_list)
    assert news_count == settings.NEWS_COUNT_ON_HOME_PAGE


# Проверяем, что новости отсортированы от самой свежей к самой старой.
# Свежие новости в начале списка.
@pytest.mark.django_db
def test_news_order(client, url_home):
    response = client.get(url_home)
    object_list = response.context['object_list']
    all_dates = [news.date for news in object_list]
    sorted_dates = sorted(all_dates, reverse=True)
    assert all_dates == sorted_dates


# Проверяем, что комментарии на странице отдельной новости отсортированы
# от старых к новым: старые в начале списка, новые — в конце.
@pytest.mark.django_db
def test_comments_order(client, author, news, url_detail):
    now = timezone.now()
    for index in range(2):
        comment = Comment.objects.create(
            news=news, author=author, text=f'Tекст {index}',
        )
        comment.created = now + timedelta(days=index)
        comment.save()
    response = client.get(url_detail)
    assert 'news' in response.context
    news = response.context['news']
    all_comments = news.comment_set.all()
    assert all_comments[0].created <= all_comments[1].created


# Проверяем, что анонимному пользователю не видна форма для отправки
# комментария на странице отдельной новости
@pytest.mark.django_db
def test_anonymous_client_has_no_form(client, url_detail):
    response = client.get(url_detail)
    assert 'form' not in response.context


# Проверяем, что авторизованному пользователю видна форма для отправки
# комментария на странице отдельной новости
@pytest.mark.django_db
def test_authorized_client_has_form(client, author, url_detail):
    client.force_login(author)
    response = client.get(url_detail)
    assert 'form' in response.context
