import os
import requests
from flask import Flask, request, jsonify, render_template_string
import urllib3
import markdown

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

MAX_AUTH = "Bearer MmJiM2FmMjMtMjk3NS00ZGVkLWFjNTAtMjIyYTJlOTFlOGM1OmQ5MmM5NDNhLTA1MTQtNDQ0Mi05N2Y1LWI2Zjk5ZDYzN2Q5Mg=="
SCOPE = "GIGACHAT_API_PERS"


def get_gigachat_token():
    response = requests.post(
        "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "RqUID": "12345678-1234-1234-1234-1234567890ab",
            "Authorization": MAX_AUTH
        },
        data={"scope": SCOPE},
        verify=False
    )
    print("Ответ на авторизацию:", response.text)
    try:
        return response.json().get("access_token")
    except:
        return None


import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_search_email(to_email, query, title, answer_html):
    from_email = "noreply@rafraf.bizml.ru"
    from_password = "8eWQkwCGxsxuipJqcJnS"
    subject = f"Поиск: {query}"

    html_content = f"""
    <h2>Запрос:</h2>
    <p>{query}</p>
    <h2>Заголовок от GigaChat:</h2>
    <p>{title}</p>
    <h2>Ответ GigaChat:</h2>
    <div>{answer_html}</div>
    """

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(html_content, 'html'))

    try:
        with smtplib.SMTP_SSL('smtp.mail.ru', 465) as server:
            server.login(from_email, from_password)
            server.sendmail(from_email, to_email, msg.as_string())
            print(f"Письмо отправлено на {to_email}")
    except Exception as e:
        print(f"Ошибка при отправке письма: {e}")


@app.route("/")
def index():
    with open("templates/base.html", encoding="utf-8") as f:
        return render_template_string(f.read())


@app.route("/search", methods=["POST"])
def search():
    query = request.form.get("query")
    if not query:
        return jsonify({"answer": "Пустой запрос."})

    token = get_gigachat_token()
    if not token:
        return jsonify({"answer": "Не удалось получить токен от GigaChat."})

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Запрос на форматированный ответ как блог-пост от модели MAX
    prompt_article = (
        "Представь, что ты ведёшь блог о программировании и робототехнике. "
        "Напиши интересную, дружелюбную статью по следующей теме, начиная со вступления вроде: \"Всем привет! Сегодня я расскажу...\".\n\n"
        + query
    )

    payload_answer = {
        "model": "GigaChat-2-Max",
        "messages": [
            {"role": "user", "content": prompt_article}
        ]
    }
    response = requests.post(
        "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
        json=payload_answer,
        headers=headers,
        verify=False
    )

    print("Ответ от GigaChat:", response.text)

    if response.ok and "choices" in response.json():
        answer = response.json()["choices"][0]["message"]["content"]
    else:
        return jsonify({"answer": "Ошибка от GigaChat: " + response.text})

    # Отдельный запрос на короткий заголовок тоже от модели MAX
    payload_title = {
        "model": "GigaChat-2",
        "messages": [
            {"role": "user", "content": f"Сформулируй короткий и понятный заголовок для этой задачи: {query}"}
        ]
    }
    response_title = requests.post(
        "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
        json=payload_title,
        headers=headers,
        verify=False
    )

    print("Заголовок от GigaChat:", response_title.text)

    if response_title.ok and "choices" in response_title.json():
        title = response_title.json()["choices"][0]["message"]["content"].strip().strip('"')
    else:
        title = query

    html_answer = markdown.markdown(answer)
    send_search_email("bikteev04@mail.ru", query, title, html_answer)

    return jsonify({
        "title": title,
        "answer": f"<div class='answer'>{answer}</div>"
    })


if __name__ == "__main__":
    app.run(debug=True)
