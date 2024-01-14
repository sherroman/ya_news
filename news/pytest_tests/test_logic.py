from http import HTTPStatus
from django.urls import reverse
import pytest
from news.forms import BAD_WORDS, WARNING
from news.models import Comment, News
from pytest_django.asserts import assertRedirects, assertFormError
from django.contrib.auth import get_user_model

User = get_user_model()
COMMENT_TEXT = 'Текст комментария'
NEW_COMMENT_TEXT = 'Обновлённый комментарий'


@pytest.fixture
def news():
    return News.objects.create(title='Заголовок', text='Текст новости')


@pytest.fixture
def comment(news, author):
    return Comment.objects.create(
        text=COMMENT_TEXT,
        news=news,
        author=author
    )


@pytest.fixture
def author(django_user_model):
    return django_user_model.objects.create(username='Автор')


@pytest.fixture
def reader(django_user_model):
    return django_user_model.objects.create(username='Читатель')


@pytest.fixture
def author_client(author, client):
    client.force_login(author)
    return client


@pytest.fixture
def reader_client(reader, client):
    client.force_login(reader)
    return client


@pytest.fixture
def form_data():
    return {'text': NEW_COMMENT_TEXT}


@pytest.fixture
def url_detail(news):
    return reverse('news:detail', args=(news.id,))


@pytest.fixture
def bad_words_data():
    return {'text': f'Какой-то текст, {BAD_WORDS[0]}, еще текст'}


@pytest.fixture
def news_url(news):
    return reverse('news:detail', args=(news.id,))


@pytest.fixture
def url_to_comments(news_url):
    return (news_url + '#comments')


@pytest.fixture
def delete_url(comment):
    return reverse('news:delete', args=(comment.id,))


@pytest.fixture
def edit_url(comment):
    return reverse('news:edit', args=(comment.id,))


# Проверяем, что анонимный пользователь не может оставить комментарий
@pytest.mark.django_db
def test_anonymous_user_cant_create_comment(client, form_data, url_detail):
    client.post(url_detail, data=form_data)
    comments_count = Comment.objects.count()
    assert comments_count == 0


# Проверяем, что авторизованный пользователь может отправить комментарий,
# перенаправляется на страницу отдельной новости и содержимое полей
# комментария соответствует ожидаемому
def test_user_can_create_comment(
    author_client, news, form_data, url_detail, author
):
    response = author_client.post(url_detail, data=form_data)
    assertRedirects(response, f'{url_detail}#comments')
    comments_count = Comment.objects.count()
    assert comments_count == 1
    comment = Comment.objects.get()
    assert comment.text == form_data['text']
    assert comment.news == news
    assert comment.author == author


# Проверяем, что сли комментарий содержит запрещённые слова, он не будет
# опубликован, а форма вернёт ошибку.
def test_user_cant_use_bad_words(author_client, bad_words_data, url_detail):
    response = author_client.post(url_detail, data=bad_words_data)
    assertFormError(
        response,
        form='form',
        field='text',
        errors=WARNING
    )
    comments_count = Comment.objects.count()
    assert comments_count == 0


# Проверяем, что авторизованный пользователь может удалять свои комментарии.
def test_author_can_delete_comment(author_client, delete_url, url_to_comments):
    response = author_client.delete(delete_url)
    assertRedirects(response, url_to_comments)
    comments_count = Comment.objects.count()
    assert comments_count == 0


# Проверяем, что авторизованный пользователь не может удалять свои комментарии
# и выпадает ошиибка 404
def test_user_cant_delete_comment_of_another_user(reader_client, delete_url):
    response = reader_client.delete(delete_url)
    assert response.status_code == HTTPStatus.NOT_FOUND
    comments_count = Comment.objects.count()
    assert comments_count == 1


# Проверяем, что авторизованный пользователь не может редактировать
# чужие комментарии.
def test_author_can_edit_comment(
    author_client, comment, edit_url, form_data, url_to_comments
):
    response = author_client.post(edit_url, data=form_data)
    assertRedirects(response, url_to_comments)
    comment.refresh_from_db()
    assert comment.text == NEW_COMMENT_TEXT


# Проверяем, что авторизованный пользователь не может удалять
# чужие комментарии.
def test_user_cant_edit_comment_of_another_user(
    reader_client, comment, edit_url, form_data
):
    response = reader_client.post(edit_url, data=form_data)
    assert response.status_code == HTTPStatus.NOT_FOUND
    comment.refresh_from_db()
    assert comment.text == COMMENT_TEXT
