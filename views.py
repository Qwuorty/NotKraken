import datetime
import time
import requests
import qrcode
from django.shortcuts import render
import random
import sqlite3
import os
import base64
import pandas as pd
import json
import string
import smtplib
from email.header import Header
from email.mime.text import MIMEText
from PIL import Image, ImageDraw, ImageFont
from rest_framework.decorators import api_view
import datetime as dt
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_200_OK, HTTP_502_BAD_GATEWAY
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import re
from django.http import HttpResponse
import httplib2
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials






TOK = "6829204293:AAH1WWHLUaTtwHyZ8oFnyZNkYHxzQGnvNyo"
Coder_token = '7172771240:AAHhuCA7TggtHqLQ1mPawPMmrlUOuYE4jPA'
coder_username = 'coder_shop_bot'
admins = [811073879, 1047465317, 547523349]


def home(request):
    return render(request, 'home.html')


def add_oper(ind, cursor, db):
    s = str(dt.datetime.now())
    s = s[:s.find(':', s.find(':') + 1)]
    if cursor.execute(f"SELECT * FROM traffic_limit WHERE ind='{ind}' AND time='{s}'").fetchone():
        cnt = int(cursor.execute(f"SELECT cnt FROM traffic_limit WHERE ind='{ind}' AND time='{s}'").fetchone()[0])
        if cnt >= 100:
            return True
        else:
            cursor.execute(f"UPDATE traffic_limit SET cnt=cnt+1 WHERE ind='{ind}' AND time='{s}'")
            db.commit()
    else:
        cursor.execute(f"DELETE FROM 'traffic_limit' WHERE ind='{ind}'")
        cursor.execute(f"INSERT INTO traffic_limit ('ind','time','cnt') VALUES ('{ind}','{s}','{1}')")
        db.commit()
    return False


def get_cost(rubles, cursor):
    ves = 2
    if rubles == '-':
        return 0
    uan = cursor.execute(f"SELECT uan FROM sys").fetchone()[0]
    uan = float(uan)
    s = str(int(((rubles + (rubles * 0.04 + 40 * ves + 25 + 5)) * uan) * 1.25))
    return s[:-3] + ' ' + s[-3:]


def get_uans(rubles, cursor):
    if rubles == 0:
        return 0
    uan = cursor.execute(f"SELECT uan FROM sys").fetchone()[0]
    cost = rubles / 1.25
    cost = cost / uan
    cost -= 110
    cost /= 1.04
    return int(cost)


def add_logs(cursor, db, oper):
    cursor.execute(
        f"INSERT INTO logs ('log') VALUES ('{oper}')")
    db.commit()


def check_token(token):
    dbs = sqlite3.connect('C:/inetpub/wwwroot/backend_api/coder.db', check_same_thread=False)
    cursor = dbs.cursor()
    response = cursor.execute(f"SELECT token,date FROM tokens WHERE token='{token}'").fetchone()
    if response is None:
        return -1  # Токена не существует
    token, date = response
    start_date = datetime(map(int, date.split('-')))
    current_date = datetime.now()
    days_difference = (current_date - start_date).days

    if days_difference > 2:
        print("Прошло больше одного дня с указанной даты.")
    else:
        print("Не прошло еще больше одного дня с указанной даты.")


def make_uan_to_rub_coder(cena):
    uan = 12
    s = str(int(cena * uan * 0.02 + cena * uan + 700 + (500 if cena < 850 else cena * uan * 0.05)))
    return s[:-3] + ' ' + s[-3:]


def make_rub_to_uan_coder(price):
    price = int(price)
    uan = 12
    cena = (price - 1200) / (uan * 0.02 + uan)
    if cena >= 850:
        cena = (price - 700) / (uan * 0.02 + uan + uan * 0.05)
    return round(cena)


@api_view(['GET', 'POST'])
def users_list(request):
    if request.method == 'POST':  # если это запрос к api от фронта
        if request.data.get('ping', False):
            db = sqlite3.connect('C:/inetpub/wwwroot/backend_api/new_db.db', check_same_thread=False)
            cursor = db.cursor()
            oper = request.data.get('oper')

            if oper == 'get_brands_list':
                ''' получает список уникальных брендов '''
                brands = cursor.execute("SELECT DISTINCT brand FROM items").fetchall()
                brands = [brand[0] for brand in brands]
                return Response({'brands': brands})

            elif oper == 'get_brand_cost':
                ''' получает максимальную и минимальную цену для каждого бренда из списка '''
                try:
                    brands = request.data.get('brands')
                    if not brands:
                        return Response('Не передан параметр brands', status=409)
                    ans = {}
                    for brand in brands:
                        response = cursor.execute(
                            "SELECT MAX(price) AS max_value, MIN(price) AS min_value FROM items WHERE brand=?",
                            (brand,)
                        ).fetchone()
                        ans[brand] = {'max': response[0], 'min': response[1]}
                    return Response(ans)
                except Exception as ex:
                    return Response({'error': str(ex)}, status=469)

            elif oper == 'get_cards_by_tov_ids':
                ''' получает карточки товаров по их артикулам '''
                try:
                    articles = request.data.get('articles')
                    if not articles:
                        return Response('Не передан параметр articles', status=469)
                    ret_arr = []
                    for article in articles:
                        arr = cursor.execute("SELECT * FROM items WHERE article=?", (article,)).fetchone()
                        if arr is None:
                            continue
                        name = arr[1]
                        folder = arr[6]
                        tov_id = arr[0]

                        with open(f'C:/inetpub/wwwroot/backend_api/media/folders/{folder}/photo_1.png', 'rb') as f:
                            s = f.read()
                        image = base64.b64encode(s).decode('utf-8')
                        slov = {
                            'id': tov_id,
                            'name': name,
                            'brand': arr[3],
                            'price': arr[4],
                            'kraken_coin': '404',
                            'photo': image
                        }
                        ret_arr.append(slov)
                    return Response({'list': ret_arr})
                except Exception as ex:
                    return Response({'er': str(ex)}, status=401)

            elif oper == 'get_top_brand_info':
                ''' получает информацию о топ-5 брендах по количеству товаров '''
                try:
                    query = """
                    SELECT brand, COUNT(id) AS count, MIN(price) AS min_price
                    FROM items
                    GROUP BY brand
                    ORDER BY count DESC
                    LIMIT 5;
                    """
                    top_brands = pd.read_sql_query(query, db)
                    return Response({'ans': top_brands.to_dict(orient='records')})
                except Exception as ex:
                    return Response({'er': str(ex)}, status=401)



            elif oper == 'get_photo_by_article':
                ''' возвращает фотографию товара по артикулу и номеру фотографии '''
                article = request.data.get('article')
                try:
                    if not article:
                        return Response({'error': 'Не передан параметр article'}, status=401)
                    num = int(request.data.get('num', '1'))
                    if str(num) == '-1':
                        num = '1'
                    # Попытка получить код фотографии из базы данных
                    photo_code = cursor.execute(
                        "SELECT photo_code FROM item_photos WHERE article=? AND photo_num=?",
                        (article, num)
                    ).fetchone()
                    if photo_code and photo_code[0]:
                        # Код фотографии найден, возвращаем его
                        return Response({'photo': photo_code[0]})
                    else:
                        # Код фотографии не найден, читаем фотографию с диска
                        folder = cursor.execute(
                            "SELECT photo_id FROM items WHERE article=?",
                            (article,)
                        ).fetchone()
                        if not folder:
                            return Response({'error': 'Товар не найден'}, status=404)
                        folder = folder[0]
                        photo_path = f'C:/inetpub/wwwroot/backend_api/media/folders/{folder}/photo_{num}.png'
                        try:
                            with open(photo_path, 'rb') as f:
                                s = f.read()
                            image = base64.b64encode(s).decode('utf-8')
                            # Сохраняем код фотографии в базу данных для будущих запросов
                            cursor.execute(
                                "INSERT INTO item_photos (article, photo_num, photo_code) VALUES (?, ?, ?)",
                                (article, num, image)
                            )
                            db.commit()
                            return Response({'photo': image})
                        except FileNotFoundError:
                            return Response({'error': 'Фото не найдено'}, status=404)
                        except Exception as ex:
                            return Response({'error': str(ex)}, status=500)
                except Exception as ex:
                    return Response({'error': str(ex)}, status=500)


            elif oper == 'get_busket_counts':
                ''' возвращает количество товаров в корзине пользователя по номеру телефона '''
                try:
                    user_phone = request.data.get('phone')
                    if not user_phone:
                        return Response({'error': 'Не передан параметр phone'}, status=401)
                    count = cursor.execute("SELECT COUNT(*) FROM busket WHERE phone=?", (user_phone,)).fetchone()[0]
                    return Response({'count': count})
                except Exception as ex:
                    return Response({'status': 'not_ok', 'error': str(ex)})

            elif oper == 'delete_item_from_busket':
                ''' удаляет товар из корзины по номеру телефона, артикулу и размеру '''
                try:
                    user_phone = request.data.get('phone')
                    item_article = request.data.get('article')
                    item_size = request.data.get('size')
                    if not all([user_phone, item_article, item_size]):
                        return Response({'error': 'Не переданы необходимые параметры'}, status=401)
                    cursor.execute(
                        "DELETE FROM busket WHERE phone=? AND article=? AND size=?",
                        (user_phone, item_article, item_size)
                    )
                    db.commit()
                    return Response({'status': 'ok'})
                except Exception as ex:
                    return Response({'status': 'not_ok', 'error': str(ex)})

            elif oper == 'get_cashback':
                ''' возвращает кэшбэк для списка товаров '''
                try:
                    item_articles = request.data.get('articles')
                    if not item_articles:
                        return Response({'error': 'Не передан параметр articles'}, status=401)
                    cashback_values = [69] * len(item_articles)
                    return Response({'cashback': cashback_values})
                except Exception as ex:
                    return Response({'status': 'not_ok', 'error': str(ex)})

            elif oper == 'make_offer':
                ''' обрабатывает создание предложения '''
                return Response({'ok': True})

            elif oper == 'get_list_by_search':
                ''' возвращает список товаров по поисковому запросу и фильтрам '''
                try:
                    ask = request.data.get('ask', '')
                    gen = request.data.get('gen')
                    cost_min = request.data.get('cost_min', 0)
                    cost_max = request.data.get('cost_max', int(1e9))
                    categories = request.data.get('categories', [])
                    brands = request.data.get('brands', [])

                    if gen is None:
                        return Response({'error': 'Не передан параметр gen'}, status=401)

                    slov_car = {
                        'underpants': (16, 17), 'shoes': (1, 2), 'tshorts': (12, 13), 'pants': (6, 8),
                        'accessories': (3, 3), 'shorts': (6, 8), 'hoodies': (14, 15), 'jackets': (4, 5),
                        'bags': (18, 18), 'dresses': (-1, 10), 'skirts': (-1, 11)
                    }
                    categories_ids = [slov_car[cat][gen] for cat in categories if cat in slov_car]
                    c_min = make_rub_to_uan_coder(int(cost_min))
                    c_max = make_rub_to_uan_coder(int(cost_max))

                    query = "SELECT DISTINCT article FROM items WHERE description!='' AND price BETWEEN ? AND ? AND price!=1000000000"
                    params = [c_min, c_max]

                    if ask:
                        query += " AND description LIKE ?"
                        params.append(f"%{ask}%")

                    if categories_ids:
                        placeholders = ', '.join('?' for _ in categories_ids)
                        query += f" AND category_id IN ({placeholders})"
                        params.extend(categories_ids)

                    if brands:
                        placeholders = ', '.join('?' for _ in brands)
                        query += f" AND brand IN ({placeholders})"
                        params.extend(brands)

                    cursor.execute(query, params)
                    ans = cursor.fetchall()
                    articles = [a[0] for a in ans]
                    return Response({'articles': articles})
                except Exception as ex:
                    return Response({'error': str(ex)}, status=401)

            elif oper == 'get_item_info':
                ''' получает информацию о товаре по артикулу '''
                try:
                    article = request.data.get('article')
                    phone = request.data.get('phone')
                    if not all([article, phone]):
                        return Response({'error': 'Не переданы необходимые параметры'}, status=401)
                    is_liked = bool(
                        cursor.execute("SELECT 1 FROM likes WHERE phone=? AND article=?", (phone, article)).fetchone())
                    info = cursor.execute("SELECT * FROM items WHERE article=?", (article,)).fetchone()
                    if not info:
                        return Response({'error': 'Товар не найден'}, status=404)
                    tov_id, name, category, brand, price, last_update, photo_id, article = info
                    folder_path = f'C:/inetpub/wwwroot/backend_api/media/folders/{photo_id}'
                    photo_cnt = len(os.listdir(folder_path))
                    return Response({
                        'name': name,
                        'category': category,
                        'brand': brand,
                        'price': price,
                        'photo_cnt': photo_cnt,
                        'is_liked': is_liked
                    })
                except Exception as ex:
                    return Response({'er': str(ex)}, status=401)

            elif oper == 'get_sizes_by_article':
                ''' возвращает список доступных размеров и цен по артикулу товара '''
                try:
                    article = request.data.get('article')
                    if not article:
                        return Response({'error': 'Не передан параметр article'}, status=401)
                    idd = cursor.execute("SELECT id FROM items WHERE article=?", (article,)).fetchone()
                    if not idd:
                        return Response({'error': 'Товар не найден'}, status=404)
                    idd = idd[0]
                    sizes_data = cursor.execute("SELECT sz FROM sizes WHERE id=?", (idd,)).fetchone()
                    if not sizes_data:
                        return Response({'sizes': []})
                    sizes_list = sizes_data[0].split(';')
                    sizes = []
                    for size_info in sizes_list:
                        size_parts = size_info.split(',')
                        size = size_parts[0]
                        price = ''.join(size_parts[1:]) if len(size_parts) > 1 else '-'
                        sizes.append([size, price])
                    return Response({'sizes': sizes})
                except Exception as ex:
                    return Response({'er': str(ex)}, status=469)

            elif oper == 'like_item':
                ''' добавляет товар в список избранного пользователя '''
                try:
                    article = request.data.get('article')
                    phone = request.data.get('phone')
                    if not all([article, phone]):
                        return Response({'error': 'Не переданы необходимые параметры'}, status=401)
                    cursor.execute("INSERT INTO likes (article, phone) VALUES (?, ?)", (article, phone))
                    db.commit()
                    return Response({'ok': True})
                except Exception as ex:
                    return Response({'error': str(ex)})

            elif oper == 'unlike_item':
                ''' удаляет товар из списка избранного пользователя '''
                try:
                    article = request.data.get('article')
                    phone = request.data.get('phone')
                    if not all([article, phone]):
                        return Response({'error': 'Не переданы необходимые параметры'}, status=401)
                    cursor.execute("DELETE FROM likes WHERE article=? AND phone=?", (article, phone))
                    db.commit()
                    return Response({'ok': True})
                except Exception as ex:
                    return Response({'error': str(ex)})

            elif oper == 'get_likes':
                ''' получает список избранных товаров пользователя '''
                try:
                    phone = request.data.get('phone')
                    if not phone:
                        return Response({'error': 'Не передан параметр phone'}, status=401)
                    likes_list = cursor.execute("SELECT article FROM likes WHERE phone=?", (phone,)).fetchall()
                    likes_list = [item[0] for item in likes_list]
                    return Response({'likes_list': likes_list})
                except Exception as ex:
                    return Response({'error': str(ex)})

            elif oper == 'add_item':
                ''' добавляет товар в корзину пользователя '''
                try:
                    article = request.data.get('article')
                    phone = request.data.get('phone')
                    size = request.data.get('size')
                    type_of_delivery = request.data.get('type_of_delivery')
                    if not all([article, phone, size]):
                        return Response({'error': f'Не переданы необходимые параметры'}, status=401)
                    if type_of_delivery is None:
                        return Response({'error':'Не передан тип доставки'},status=401)
                    cursor.execute("INSERT INTO busket (article, phone, size) VALUES (?, ?, ?)", (article, phone, size))
                    db.commit()
                    return Response({'ok': True})
                except Exception as ex:
                    return Response({'error': str(ex)})

            elif oper == 'get_busket':
                ''' получает содержимое корзины пользователя '''
                try:
                    phone = request.data.get('phone')
                    if not phone:
                        return Response({'error': 'Не передан параметр phone'}, status=401)
                    busket_items = cursor.execute(
                        "SELECT item_id, article, size FROM busket WHERE phone=?", (phone,)
                    ).fetchall()
                    busket = [{'item_id': item_id, 'article': article, 'size': size} for item_id, article, size in
                              busket_items]
                    return Response({'busket': busket})
                except Exception as ex:
                    return Response({'error': str(ex)})


        elif request.data.get('flag', False) == True:
            dbs = sqlite3.connect('C:/inetpub/wwwroot/backend_api/coder.db', check_same_thread=False)
            cursor = dbs.cursor()
            if request.data.get('oper') == 'check_correct_bot_code':
                if bool(cursor.execute(f"SELECT * FROM users WHERE check_code={request.data.get('code')}").fetchone()):
                    chat_id = \
                        cursor.execute(f"SELECT * FROM users WHERE check_code='{request.data.get('code')}'").fetchone()[
                            0]
                    requests.post(
                        f'https://api.telegram.org/bot{Coder_token}/sendMessage?chat_id={chat_id}&text="в ваш аккаунт вошли"')
                    return Response(
                        {'status': 'ok', 'chat_id': chat_id})
                else:
                    return Response({'status': 'error'})
            elif request.data.get('oper') == 'get_brands_list':
                brands = cursor.execute(f"SELECT DISTINCT brand FROM items").fetchall()
                return Response({'brands': list(sorted(list(brands)))})
            elif request.data.get('oper') == 'set_account_info_by_id':
                if not request.data.get('chat_id', False):
                    return Response({'error': 'Нет chat_id в получаемом json'})
                chat_id = request.data.get('chat_id')
                if request.data.get('name', False):
                    name = request.data.get('name')
                    if len(name) > 60 or name == '':
                        return Response({'error': 'Имя слишком длинное'}, status=401)
                    cursor.execute(f"UPDATE users SET name='{request.data.get('name')}' WHERE chat_id='{chat_id}'")
                if request.data.get('surname', False):
                    surname = request.data.get('surname')
                    if len(surname) > 60 or surname == '':
                        return Response({'error': 'Фамилия слишком длинная'}, status=401)
                    cursor.execute(
                        f"UPDATE users SET surname='{request.data.get('surname')}' WHERE chat_id='{chat_id}'")
                if request.data.get('phone', False):
                    cursor.execute(f"UPDATE users SET phone='{request.data.get('phone')}' WHERE chat_id='{chat_id}'")
                if request.data.get('address', False):
                    cursor.execute(
                        f"UPDATE users SET address='{request.data.get('address')}' WHERE chat_id='{chat_id}'")
                dbs.commit()
                return Response({'status': 'ok'})
            elif request.data.get('oper') == 'get_account_info_by_id':
                if not request.data.get('chat_id', False):
                    return Response({'error': 'Нет chat_id в получаемом json'})
                chat_id = request.data.get('chat_id')
                info = cursor.execute(f"SELECT * FROM users WHERE chat_id='{chat_id}'").fetchone()
                user_info = {}
                user_info['name'] = '' if info[3] is None else info[3]
                user_info['surname'] = '' if info[4] is None else info[4]
                user_info['phone'] = '' if info[5] is None else info[5]
                user_info['address'] = '' if info[6] is None else info[6]
                return Response(user_info)

            elif request.data.get('oper') == 'make_last_offer':
                try:
                    if not request.data.get('chat_id', False):
                        return Response({'error': 'Нет chat_id в получаемом json'})
                    chat_id = request.data.get('chat_id')
                    if not request.data.get('busket', False):
                        return Response({'error': 'Нет busket в получаемом json'})
                    busket = request.data.get('busket')
                    last_id = cursor.execute(f"SELECT MAX(offer_id) AS offer_id FROM open_offers").fetchone()[0]
                    if last_id is None:
                        last_id = 0
                    else:
                        last_id = int(last_id)
                    new_id = last_id + 1
                    for i in busket:
                        article = i['article']
                        cnt = int(i['cnt'])
                        size = i['size']
                        cost = i['cost'].replace(' ','')
                        cursor.execute(
                            f"INSERT INTO open_offers (chat_id, article, size, cnt,cost, status,offer_id) VALUES ('{chat_id}',"
                            f"'{article}','{size}','{cnt}','{cost}',0,{new_id})")
                        # cursor.execute(F"DELETE FROM orders WHERE chat_id='{chat_id}' AND article='{article}' AND size='{size}'")
                        dbs.commit()

                    admin_id = 5498270319#5498270319#811073879
                    token = '7172771240:AAHhuCA7TggtHqLQ1mPawPMmrlUOuYE4jPA'
                    username = cursor.execute(f"SELECT username FROM users WHERE chat_id='{chat_id}'").fetchone()[0]
                    text=f'Внимание, новый заказ от @{username}\nНомер заказа - {new_id}'
                    reply_markup = {
                        "inline_keyboard": [[{"text": "Посмотреть инфу", "callback_data": f"offer:0:{chat_id}:{new_id}"}],
                                            [{"text": "Связаться с пользователем",
                                              "callback_data": f"offer:1:{chat_id}:{new_id}"}]]
                        }
                    data = {
                        'chat_id': admin_id,
                        'text': text,
                        'reply_markup': json.dumps(reply_markup)  # Сериализуем в JSON
                    }
                    msg = requests.post(
                        f'https://api.telegram.org/bot{token}/sendMessage', json=data)

                    return Response({'ans':msg},200)
                    #нужно связать админа и пользователя через бота
                    #добавит в гт новый заказ
                except Exception as ex:
                    return Response({'error':str(ex)},status=469)


            elif request.data.get('oper') == 'get_last_bill':
                try:
                    if not request.data.get('chat_id', False):
                        return Response({'error': 'Нет chat_id в получаемом json'})
                    chat_id = request.data.get('chat_id')
                    if not request.data.get('busket', False):
                        return Response({'error': 'Нет busket в получаемом json'})
                    busket = request.data.get('busket')
                    cost = 0
                    for i in busket:
                        article = i['article']
                        tov_id = cursor.execute(f"SELECT id FROM items WHERE article ='{article}'").fetchone()[0]
                        cnt = int(i['cnt'])
                        size = i['size']
                        sizes = cursor.execute(f"SELECT sz FROM sizes WHERE id='{tov_id}'").fetchone()[0].split(';')
                        for sz in sizes:
                            item = sz.split(',')
                            if item[0].strip() == size.strip():
                                cost += cnt * int(make_uan_to_rub_coder(int(item[1].replace('.', ''))).replace(' ', ''))
                                break
                    cost = str(cost)
                    return Response({"cost": cost[:-3] + ' ' + cost[-3:]})
                except Exception as ex:
                    return Response({'error': str(ex)}, 469)

                # Получаем карзину, считаем общую сумму заказа, возвращаем ее в ответе
                # Оповещаем админов о заказе
                # Если пользователь прислал чек, то пересылаем его админу
                # Если через 5 минут послее открытия чека - ничего не произошло - отправляем человеку в ТГ сообщение с оповещением


            elif request.data.get('oper') == 'get_list_by_search':
                try:
                    '''Добавляет в базу данных количество к популярности товара '''
                    if 'ask' not in request.data.keys():
                        return Response({'error': 'Текст запроса не передан'}, status=401)
                    ask = request.data.get('ask')

                    if 'gen' not in request.data.keys():
                        return Response({'error': 'gen не передан'}, status=401)
                    gen = request.data.get('gen')

                    if 'cost_min' not in request.data.keys():
                        return Response({'error': 'Неправильный формат cost_min'}, status=401)
                    cost_min = request.data.get('cost_min')

                    if 'cost_max' not in request.data.keys():
                        return Response({'error': 'Неправильный формат cost_max'}, status=401)

                    if 'categories' not in request.data.keys():
                        return Response({'error': 'Неправильный формат categories'}, status=401)

                    if 'brands' not in request.data.keys():
                        return Response({'error': 'Неправильный формат brands'}, status=401)

                    categories = list(request.data.get('categories'))
                    slov_car = {'underpants': (16, 17), 'shoes': (1, 2), 'tshorts': (12, 13), 'pants': (6, 8),
                                'accessories': (3, 3), 'shorts': (6, 8), 'hoodies': (14, 15), 'jackets': (4, 5),
                                'bags': (18, 18), 'dresses': (-1, 10), 'skirts': (-1, 11)}

                    for i in range(len(categories)):
                        categories[i] = slov_car[categories[i]][gen]

                    brands = request.data.get('brands')
                    cost_max = request.data.get('cost_max')

                    if cost_min == '':
                        cost_min = 0
                    if cost_max == '':
                        cost_max = int(1e9)

                    try:
                        c_min = make_rub_to_uan_coder(int(cost_min))
                        c_max = make_rub_to_uan_coder(int(cost_max))

                        query = "SELECT DISTINCT article FROM items WHERE description!='' AND price>=? AND price<=? AND price!=1000000000 "
                        params = [c_min, c_max]

                        if ask:
                            like_pattern = f"%{ask}%"
                            query += " AND description LIKE ?"
                            params.append(like_pattern)

                        if categories:
                            placeholders = ', '.join('?' for _ in categories)
                            query += f" AND category_id IN ({placeholders})"
                            params.extend(categories)

                        if brands:
                            placeholders = ', '.join('?' for _ in brands)
                            query += f" AND brand IN ({placeholders})"
                            params.extend(brands)

                        # Добавляем сортировку
                        if 'sort_type' in request.data.keys():
                            sort_type = request.data.get('sort_type')
                            if sort_type == 1:
                                query += " ORDER BY price DESC"
                            elif sort_type == 2:
                                query += " ORDER BY price ASC"
                            elif sort_type == 3:
                                query += " ORDER BY popular DESC"
                            else:
                                return Response({'error': 'Неправильный тип сортировки'}, status=400)

                        cursor.execute(query, params)

                        ans = cursor.fetchall()
                        for i in range(len(ans)):
                            ans[i] = ans[i][0]

                        return Response({'articles': ans})

                    except Exception as ex:
                        return Response({'error': str(ex)}, 421)
                except Exception as ex:
                    return Response({'error': str(ex)}, 401)



            elif request.data.get('oper') == 'get_item_info_by_id':
                '''возвращаем инфу о товаре по его id ('id':x) -> ('description':x 'brand':x,'price':x,'name':x  '''
                try:
                    chat_id = request.data.get('chat_id')
                    ret_arr = []
                    if 'ask_articles' not in request.data.keys():
                        return Response({'error': 'ask_articles не передан'}, status=401)

                    for i in request.data.get('ask_articles'):
                        arr = cursor.execute(f"SELECT * FROM items WHERE article='{i}'").fetchone()
                        cursor.execute(f"UPDATE items SET popular=popular+1 WHERE article='{i}'")
                        dbs.commit()
                        folder = arr[6]
                        tov_id = i
                        if not (arr):
                            return Response({'answer': 0})
                        s = open(f'C:/inetpub/wwwroot/backend_api/media/small_img/{folder}.jpg', 'rb').read()
                        image = base64.b64encode(s)
                        cnt = cursor.execute(f"SELECT score FROM rating WHERE article='{i}'").fetchall()
                        stars_cnt = 0
                        for j in cnt:
                            stars_cnt += int(j[0])
                        cnt = len(cnt)
                        slov = {'article': arr[-2].split('\n'), 'answer': 1, 'description': '.!.', 'name': arr[1],
                                'brand': arr[3],
                                'price': 'Нет в наличии' if int(arr[4]) == -1 else make_uan_to_rub_coder(int(arr[4])),
                                'is_liked': bool(cursor.execute(
                                    f"SELECT * FROM likes WHERE article='{i}' AND chat_id='{chat_id}'").fetchone()),
                                'stars': '--' if cnt == 0 else stars_cnt / cnt,
                                'photo': image}
                        ret_arr.append(slov)
                    return Response({'list': ret_arr})
                except Exception as ex:
                    return Response({'er': str(ex)}, 4011)

            elif request.data.get('oper') == 'get_cnt_photos_by_tov_id':
                ''' Возвращает количество фотографий по tov_id'''
                try:
                    if 'article' not in request.data.keys():
                        return Response({'error': 'article не передан'}, status=401)
                    folder = cursor.execute(
                        f"SELECT photo_id FROM items WHERE article='{request.data.get('article')}'").fetchone()[0]
                    return Response({'cnt': len(os.listdir(f'C:/inetpub/wwwroot/backend_api/media/folders/{folder}'))})
                except Exception as ex:
                    return Response({'error': str(ex)}, status=401)

            elif request.data.get('oper') == 'get_login_link':
                '''
                    присылаем кьюар код и ссылку на него 
                '''
                uniq_id = ''.join([str(random.randint(1, 10)) for _ in range(10)])

                if cursor.execute(f"SELECT * from login_code WHERE login_id='{uniq_id}'").fetchone():
                    uniq_id = ''.join([str(random.randint(0, 9)) for _ in range(10)])

                link = f'https://t.me/{coder_username}?start={uniq_id}'
                path = 'C:/inetpub/wwwroot/backend_api/media/qr_image'
                qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10,
                                   border=4)
                qr.add_data(link)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                img.save(f"{path}/{uniq_id}.png")

                s = open(f"{path}/{uniq_id}.png", 'rb').read()
                image = base64.b64encode(s)
                os.remove(f"{path}/{uniq_id}.png")

                cursor.execute(f"INSERT INTO login_code ('login_id') VALUES ('{uniq_id}')")
                dbs.commit()
                return Response({'image': image, 'link': link, 'login_id': uniq_id})



            elif request.data.get('oper') == 'apply_login':
                if 'login_id' not in request.data.keys():
                    return Response({'error': 'Ебать ты козёл, логин айди не отправил'}, status=401)
                log_id = request.data.get('login_id')
                ans = cursor.execute(
                    f"SELECT chat_id FROM login_code WHERE login_id='{log_id}' and chat_id!='{None}'").fetchone()
                if not ans is None:
                    return Response({'ans': True, 'chat_id': ans[0]})
                else:
                    return Response({'ans': False})



            elif request.data.get('oper') == 'get_sizes_by_id':
                '''   Возвращаем двумерный массив размеров-цен по id товара ('id':'x') -> {'sizes':'x'}   '''
                if 'article' not in request.data.keys():
                    return Response({'error': 'ты козёл, article не отправил'}, status=401)
                article = request.data.get('article')
                tov_id = cursor.execute(f"SELECT id FROM items WHERE article='{article}'").fetchone()[0]
                arr = cursor.execute(f"SELECT * FROM sizes WHERE id='{tov_id}'").fetchone()[1].split(';')
                for i in range(len(arr)):
                    try:
                        a = str(make_uan_to_rub_coder(int(arr[i].split(',')[1].replace('.', '').replace(',', ''))))
                        arr[i] = [arr[i].split(',')[0], a]
                    except Exception as ex:
                        arr[i] = [arr[i].split(',')[0], '-']

                return Response({'sizes': arr})

            elif request.data.get('oper') == 'get_photo_by_tov_id':
                ''' Возвращает фотографию по id товара и ее номеру '''
                if 'article' not in request.data.keys():
                    return Response({'error': 'ты козёл, article не отправил'}, status=401)
                folder = \
                    cursor.execute(f"SELECT * FROM items WHERE article='{request.data.get('article')}'").fetchone()[6]
                try:
                    if str(request.data.get('num')) == '-1':
                        s = open(f'C:/inetpub/wwwroot/backend_api/media/small_img/{folder}.jpg', 'rb').read()
                    else:
                        s = open(
                            f'C:/inetpub/wwwroot/backend_api/media/folders/{folder}/' + f'photo_{str(request.data.get('num'))}.png',
                            'rb').read()
                    image = base64.b64encode(s)
                    return Response({'photo': image})
                except Exception as ex:
                    return Response({'photo': str(ex)})

            elif request.data.get('oper') == 'add_tov_in_busket':
                if not request.data.get('chat_id', False):
                    return Response({'error': 'Нет chat_id в получаемом json'}, 401)
                chat_id = request.data.get('chat_id')
                if not request.data.get('article', False):
                    return Response({'error': 'Нет article в получаемом json'}, 401)
                article = request.data.get('article')
                if not request.data.get('size', False):
                    return Response({'error': 'Нет size в получаемом json'}, 401)
                sz = request.data.get('size')
                if cursor.execute(
                        f"SELECT * FROM orders WHERE article='{article}' AND chat_id='{chat_id}' AND sz='{sz}'").fetchone():
                    cursor.execute(
                        f"UPDATE orders  SET cnt=cnt+1 WHERE article='{article}' AND chat_id='{chat_id}' AND sz='{sz}'")
                else:
                    cursor.execute(
                        f"INSERT INTO orders ('article','sz','chat_id','cnt') VALUES ('{article}','{sz}','{chat_id}',1)")
                dbs.commit()
                cnt = cursor.execute(f"SELECT * FROM orders WHERE chat_id='{chat_id}'").fetchall()
                cnt = len(cnt)
                return Response({"cnt": int(cnt)})

            elif request.data.get('oper') == 'get_busket':
                try:
                    if not request.data.get('chat_id', False):
                        return Response({'error': 'Нет chat_id в получаемом json'}, 401)
                    chat_id = request.data.get('chat_id')
                    arr = cursor.execute(f"SELECT * FROM orders WHERE chat_id='{chat_id}'").fetchall()
                    ans = []
                    for i in arr:
                        article = i[1]
                        size = i[2]
                        tov_id = cursor.execute(f"SELECT id FROM items WHERE article='{article}'").fetchone()[0]
                        sizes = cursor.execute(f"SELECT * FROM sizes WHERE id='{tov_id}'").fetchone()
                        for j in sizes[1].split(';'):
                            sz, cost = j.split(',')
                            if (str(sz) == str(size)):
                                ans.append({'article': article, 'size': i[2], 'cnt': i[3],
                                            'cost': make_uan_to_rub_coder(
                                                int(str(cost).replace('.', '').replace(',', '')))})
                                break
                    return Response({'items': ans})
                except Exception as ex:
                    return Response({'error': str(ex)}, 569)

            elif request.data.get('oper') == 'remove_tov_from_busket':
                try:
                    if not request.data.get('chat_id', False):
                        return Response({'error': 'Нет chat_id в получаемом json'}, 401)
                    chat_id = request.data.get('chat_id')
                    if not request.data.get('article', False):
                        return Response({'error': 'Нет article в получаемом json'}, 401)
                    article = request.data.get('article')
                    if not request.data.get('size', False):
                        return Response({'error': 'Нет size в получаемом json'}, 401)
                    sz = request.data.get('size')
                    if cursor.execute(
                            f"SELECT * FROM orders WHERE article='{article}' AND chat_id='{chat_id}' AND sz='{sz}'").fetchone():
                        if (cursor.execute(
                                f"SELECT cnt FROM orders WHERE article='{article}' AND chat_id='{chat_id}' AND sz='{sz}'").fetchone()[
                            0] == 1):
                            cursor.execute(
                                f"DELETE FROM orders WHERE article='{article}' AND chat_id='{chat_id}' AND sz='{sz}'")
                        else:
                            cursor.execute(
                                f"UPDATE orders SET cnt=cnt-1 WHERE article='{article}' AND chat_id='{chat_id}' AND sz='{sz}'")
                        dbs.commit()
                    else:
                        return Response({"status": 'deleted'})
                    return Response({"status": 'ok'})
                except Exception as ex:
                    return Response({'er': str(ex)}, 401)

            elif request.data.get('oper') == 'delete_tov_from_busket':
                if not request.data.get('chat_id', False):
                    return Response({'error': 'Нет chat_id в получаемом json'}, 401)
                chat_id = request.data.get('chat_id')
                arr = request.data.get('list')
                for i in arr:
                    sz = i.get('size')
                    cursor.execute(
                        f"DELETE FROM orders WHERE article='{i.get('article')}' AND chat_id='{chat_id}' AND sz='{sz}'")
                dbs.commit()
                return Response({"status": 'ok'})

            elif request.data.get('oper') == 'add_comment':
                if not request.data.get('chat_id', False):
                    return Response({'error': 'Нет chat_id в получаемом json'}, 401)
                chat_id = request.data.get('chat_id')
                if not request.data.get('article', False):
                    return Response({'error': 'Нет article в получаемом json'}, 401)
                article = request.data.get('article')
                if not request.data.get('comment', False):
                    return Response({'error': 'Нет comment в получаемом json'}, 401)
                comment = request.data.get('comment')
                if not request.data.get('score', False):
                    return Response({'error': 'Нет score в получаемом json'}, 401)
                score = request.data.get('score')
                cursor.execute(f"INSERT INTO rating ('article','chat_id','score','comment','date') VALUES ('{article}',"
                               f"'{chat_id}',{score},'{comment}','{str(datetime.datetime.now())}')")
                dbs.commit()
                return Response({"status": 'ok'})

            elif request.data.get('oper') == 'get_comments':
                if not request.data.get('article', False):
                    return Response({'error': 'Нет article в получаемом json'}, 401)
                article = request.data.get('article')
                cursor.execute(f"SELECT * FROM rating WHERE article='{article}'").fetchall()
                ans = []
                for i in cursor.execute(f"SELECT * FROM rating WHERE article='{article}'").fetchall():
                    tg = cursor.execute(f"SELECT username FROM users WHERE chat_id='{i[0]}'").fetchone()
                    tg = '@' + tg[0] if (not tg is None) else 'Аноним'
                    ans.append({'tg': tg, 'score': i[2], 'comment': i[3], 'date': i[4]})
                return Response(ans)


            elif request.data.get('oper') == 'add_delivery_info':
                if not request.data.get('chat_id', False):
                    return Response({'error': 'Нет chat_id в получаемом json'}, 401)
                chat_id = request.data.get('chat_id')
                if not request.data.get('info', False):
                    return Response({'error': 'Нет info в получаемом json'}, 401)
                info = request.data.get('info')
                cursor.execute(f"INSERT INTO delivery ('info','chat_id') VALUES ('{info}','{chat_id}')")
                dbs.commit()
                return Response({"status": 'ok'})


            elif request.data.get('oper') == 'delete_delivery_info':
                if not request.data.get('chat_id', False):
                    return Response({'error': 'Нет chat_id в получаемом json'}, 401)
                chat_id = request.data.get('chat_id')
                if not request.data.get('info', False):
                    return Response({'error': 'Нет info в получаемом json'}, 401)
                info = request.data.get('info')
                cursor.execute(f"DELETE FROM delivery WHERE info='{info}' AND chat_id='{chat_id}'")
                dbs.commit()
                return Response({"status": f'{info}/{chat_id}'})


            elif request.data.get('oper') == 'get_delivery_info':
                try:
                    if not request.data.get('chat_id', False):
                        return Response({'error': 'Нет chat_id в получаемом json'}, 401)
                    chat_id = request.data.get('chat_id')
                    ans = cursor.execute(f"SELECT info FROM delivery WHERE chat_id='{chat_id}'").fetchall()
                    arr = []
                    for i in ans:
                        arr.append(i[0])
                    return Response(arr)
                except Exception as ex:
                    return Response({'error': str(ex)})


            elif request.data.get('oper') == 'add_tov_in_likes':
                if not request.data.get('chat_id', False):
                    return Response({'error': 'Нет chat_id в получаемом json'}, 401)
                chat_id = request.data.get('chat_id')
                if not request.data.get('article', False):
                    return Response({'error': 'Нет article в получаемом json'}, 401)
                article = request.data.get('article')
                if not cursor.execute(
                        f"SELECT * FROM likes WHERE article='{article}' AND chat_id='{chat_id}'").fetchone():
                    cursor.execute(f"INSERT INTO likes ('article','chat_id') VALUES ('{article}','{chat_id}')")
                dbs.commit()
                return Response({"status": 'ok'})

            elif request.data.get('oper') == 'remove_tov_from_likes':
                if not request.data.get('chat_id', False):
                    return Response({'error': 'Нет chat_id в получаемом json'}, 401)
                chat_id = request.data.get('chat_id')
                if not request.data.get('article', False):
                    return Response({'error': 'Нет article в получаемом json'}, 401)
                article = request.data.get('article')
                cursor.execute(f"DELETE FROM likes WHERE article='{article}' AND chat_id='{chat_id}'")
                dbs.commit()
                return Response({"status": 'ok'})

            elif request.data.get('oper') == 'get_likes':
                if not request.data.get('chat_id', False):
                    return Response({'error': 'Нет chat_id в получаемом json'}, 401)
                chat_id = request.data.get('chat_id')
                arr = cursor.execute(f"SELECT * FROM likes WHERE chat_id='{chat_id}'").fetchall()
                ans = []
                for i in arr:
                    ans.append(i[1])
                return Response({'items': ans})


        else:
            db = sqlite3.connect('C:/inetpub/wwwroot/backend_api/local_db.db', check_same_thread=False)
            sql = db.cursor()
            if request.data.get('oper') == 'user_exist':
                '''проверяем, зарегестрирован ли пользователь  ('mail':'x') ->{'exist':true/false}'''
                add_logs(sql, db, 'user_exist')
                if add_oper(request.data.get('mail'), sql, db):
                    return Response({'error': None})
                return Response(
                    {'exist': bool(
                        sql.execute(f"SELECT * FROM users WHERE mail='{request.data.get('mail')}'").fetchone())})

            elif request.data.get('oper') == 'reg_user':
                '''регистрируем пользователя, ('mail':x,'password':x) -> None'''
                add_logs(sql, db, 'reg_user')
                mail = request.data.get('mail')
                if add_oper(request.data.get('mail'), sql, db):
                    return Response({'error': None})
                pwrd = request.data.get('password')
                sql.execute(
                    f"INSERT INTO users ('mail','password','date') VALUES ('{mail}','{pwrd}','{dt.datetime.now()}')")
                db.commit()
                return Response()

            elif request.data.get('oper') == 'update_password':
                '''Обновляет пароль для пользователя с почтой mail '''
                add_logs(sql, db, 'update_password')
                if add_oper(request.data.get('mail'), sql, db):
                    return Response({'error': None})
                sql.execute(
                    f"UPDATE users SET password='{request.data.get('new_pswrd')}' WHERE mail='{request.data.get('mail')}'")
                db.commit()
                return Response({'ok': 1})

            elif request.data.get('oper') == 'get_cost_by_id_and_size':
                '''регистрируем пользователя, ('mail':x,'password':x) -> None'''
                add_logs(sql, db, 'get_cost_by_id_and_size')
                id = request.data.get('id')
                size = request.data.get('size')
                sizes = sql.execute(f"SELECT * FROM sizes WHERE id = '{id}'").fetchone()
                if add_oper(request.data.get('mail'), sql, db):
                    return Response({'error': None})
                for i in sizes[1].split(';'):
                    sz, cost = i.split(',')
                    if (str(sz) == str(size)):
                        a = str(get_cost(int(str(cost).replace('.', '').replace(',', '')), sql))
                        return Response({'cost': a})
                return Response()

            elif request.data.get('oper') == 'check_correct_mail':
                add_logs(sql, db, 'check_correct_mail')
                ''' проверям корректность введённой почты, ('mail':x) -> 1/2/3'''
                mail = request.data.get('mail')
                idd = request.data.get('user_id')
                if add_oper(idd, sql, db):
                    return Response({'error': None})
                pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if re.match(pattern, mail) and len(mail) != '':
                    if bool(sql.execute(f"SELECT * FROM users WHERE mail='{request.data.get('mail')}'").fetchone()):
                        return Response({'answer': '2', 'msg': 'already_in'})
                    return Response({'answer': '3', 'msg': "ok"})
                else:
                    return Response({'answer': '1', 'msg': 'incorrect text'})

            elif request.data.get('oper') == 'get_photo_by_tov_id':
                add_logs(sql, db, 'get_photo_by_tov_id')

                ''' Возвращает фотографию по id товара и ее номеру '''
                folder = sql.execute(f"SELECT * FROM items WHERE id='{request.data.get('id')}'").fetchone()[6]
                try:
                    if add_oper(request.data.get('mail'), sql, db):
                        return Response({'error': None})
                    if str(request.data.get('num')) == '-1':
                        s = open(f'C:/inetpub/wwwroot/backend_api/media/small_img/{folder}.jpg', 'rb').read()
                    else:
                        s = open(
                            f'C:/inetpub/wwwroot/backend_api/media/img/{folder}/' + f'photo_{str(request.data.get('num'))}.png',
                            'rb').read()
                    image = base64.b64encode(s)
                    return Response({'photo': image})
                except Exception as ex:
                    return Response({'photo': str(ex)})


            elif request.data.get('oper') == 'get_cnt_photos_by_tov_id':
                ''' Возвращает количество фотографий по tov_id'''
                add_logs(sql, db, 'get_cnt_photos_by_tov_id')
                if add_oper(request.data.get('mail'), sql, db):
                    return Response({'error': None})
                folder = sql.execute(f"SELECT * FROM items WHERE id='{request.data.get('id')}'").fetchone()[6]
                return Response({'cnt': len(os.listdir(f'C:/inetpub/wwwroot/backend_api/media/img/{folder}'))})

            elif request.data.get('oper') == 'get_new_cookies_id':
                ''' return id for coockie'''
                add_logs(sql, db, 'get_new_cookies_id')
                new_id = ''.join([str(random.randint(1, 9)) for _ in range(35)])
                while sql.execute(f"SELECT * FROM ids WHERE id='{new_id}'").fetchone():
                    new_id = ''.join([str(random.randint(1, 9)) for _ in range(35)])
                sql.execute(f"INSERT INTO ids ('id') VALUES ('{new_id}')")
                db.commit()
                return Response({'id': new_id})


            elif request.data.get('oper') == 'create_captcha':
                add_logs(sql, db, 'create_captcha')
                '''создаём капчу ('cock_id':x) -> FileResponce'''
                # путь к папке с изображениями
                img_folder = r"C:\inetpub\wwwroot\backend_api\media\form_captcha"

                # путь к папке для сохранения измененных изображений
                output_folder = r"C:\inetpub\wwwroot\backend_api\media\captcha"

                # выбираем случайное слово из списка

                # получаем список файлов в папке с изображениями
                img_files = os.listdir(img_folder)

                # выбираем случайное изображение
                random_img = random.choice(img_files)

                # открываем выбранное изображение
                img = Image.open(os.path.join(img_folder, random_img))

                draw = ImageDraw.Draw(img)

                # Загружаем шрифт
                font = ImageFont.truetype(r'C:/inetpub/wwwroot/backend_api/arial_bold.ttf', 70)

                w, h = 350, 100
                rand_x = random.randint(50, 200)
                rand_y = random.randint(50, 420)

                # Добавляем текст на изображение
                symbols = 'qwertyuiopasdfghjklzxcvbnm1234567890'
                text = ''.join([random.choice(symbols).upper() for _ in range(5)])
                random_word = text
                colors = [(255, 192, 203), (255, 187, 153), (192, 255, 193), (173, 216, 230), (221, 160, 221),
                          (152, 251, 152)]
                draw.text((rand_x, rand_y), text, fill=random.choice(colors), font=font)
                for _ in range(2):
                    draw.line([(rand_x + 5, rand_y + random.randint(0, 65) + 15),
                               (rand_x + 240 + 5, rand_y + random.randint(0, 65) + 15)], (255, 255, 255), 6)

                # сохраняем измененное изображение в другую папку
                def generate_random_string(length):
                    letters = string.ascii_lowercase
                    return ''.join(random.choice(letters) for _ in range(length))

                # путь к папке, где будем проверять наличие файла
                folder_path = r'C:\inetpub\wwwroot\backend_api\media\captcha'

                # генерируем случайную строку длиной 30 символов
                random_string = generate_random_string(30)

                # проверяем, существует ли файл с таким именем в папке
                while os.path.exists(os.path.join(folder_path, random_string)):
                    random_string = generate_random_string(30)
                random_string += '.jpg'
                output_path = folder_path + '/' + random_string
                img.save(output_path)
                if add_oper(request.data.get('cock_id'), sql, db):
                    return Response({'error': None})
                sql.execute(
                    f"INSERT INTO captcha ('cock_id','direct','key') VALUES ('{request.data.get('cock_id')}','{random_string.lower()}','{random_word.lower()}')")
                db.commit()
                s = open(output_path, 'rb').read()
                return HttpResponse(s)


            elif request.data.get('oper') == 'check_captcha':
                '''   Проверяем капчу ('user_input':'x','cock_id':x) -> 'ans':true/false   '''
                add_logs(sql, db, 'check_captcha')
                user_input = request.data.get('user_input')
                cock_id = request.data.get('cock_id')
                if add_oper(request.data.get('cock_id'), sql, db):
                    return Response({'error': None})
                return Response({'ans': bool(
                    sql.execute(
                        f"SELECT * FROM 'captcha' WHERE cock_id='{cock_id}' AND key='{user_input.lower()}'").fetchall())})

            elif request.data.get('oper') == 'get_all_photos_by_id':
                '''   возвращаем список фоток ('id':'x') -> 'photos':[x,x,x,x]     '''
                add_logs(sql, db, 'get_all_photos_by_id')
                photo = sql.execute(f"SELECT * FROM items WHERE id='{request.data.get('id')}'").fetchone()[6]
                arr = []
                if add_oper(request.data.get('mail'), sql, db):
                    return Response({'error': None})
                for filename in os.listdir(f"../frontend/public/img/item_photos/{photo}"):
                    if os.path.isfile(os.path.join(f"../frontend/public/img/item_photos/{photo}", filename)):
                        arr.append(photo + '/' + filename)
                return Response({'photos': arr})

            elif request.data.get('oper') == 'delete_captcha':
                '''   Удаляем капчу по названию фотки   '''
                add_logs(sql, db, 'delete_captcha')
                cock_id = request.data.get('cock_id')
                sql.execute(f"DELETE FROM 'captcha' WHERE cock_id='{cock_id}'")
                if add_oper(cock_id, sql, db):
                    return Response({'error': None})
                db.commit()
                for i in os.listdir(f"C:/inetpub/wwwroot/backend_api/media/captcha"):
                    if not sql.execute(f"SELECT * FROM captcha WHERE direct='{i}'").fetchone():
                        try:
                            os.remove(f"C:/inetpub/wwwroot/backend_api/media/captcha/{i}")
                        except:
                            pass
                return Response()

            elif request.data.get('oper') == 'request_avail_size':
                add_logs(sql, db, 'request_avail_size')
                tov_id = request.data.get('tov_id')
                len1 = len(sql.execute(f"SELECT * FROM update_order").fetchall())
                len2 = len(sql.execute(f"SELECT * FROM update_order2").fetchall())
                if add_oper(request.data.get('mail'), sql, db):
                    return Response({'error': None})
                if len1 > len2:
                    sql.execute(f"INSERT INTO update_order2 ('id') VALUES ('{tov_id}')")
                    db.commit()
                else:
                    sql.execute(f"INSERT INTO update_order ('id') VALUES ('{tov_id}')")
                    db.commit()
                return Response()

            elif request.data.get('oper') == 'already_updated_tov':
                add_logs(sql, db, 'already_updated_tov')
                tov_id = request.data.get('tov_id')
                if add_oper(request.data.get('mail'), sql, db):
                    return Response({'error': None})
                if len(sql.execute(f"SELECT * FROM update_order WHERE id='{tov_id}'").fetchall()) or \
                        len(sql.execute(f"SELECT * FROM update_order2 WHERE id='{tov_id}'").fetchall()):
                    return Response({'ans': 0})
                else:
                    return Response({'ans': 1})

            elif request.data.get('oper') == 'get_sizes_by_id':
                '''   Возвращаем двумерный массив размеров-цен по id товара ('id':'x') -> {'sizes':'x'}   '''
                add_logs(sql, db, 'get_sizes_by_id')
                idd = request.data.get('id')
                arr = sql.execute(f"SELECT * FROM sizes WHERE id='{idd}'").fetchone()[1].split(';')
                if add_oper(request.data.get('mail'), sql, db):
                    return Response({'error': None})
                for i in range(len(arr)):
                    try:
                        a = str(get_cost(int(arr[i].split(',')[1].replace('.', '').replace(',', '')), sql))
                        arr[i] = [arr[i].split(',')[0], a]
                    except:
                        arr[i] = [arr[i].split(',')[0], '-']

                return Response({'sizes': arr})





            elif request.data.get('oper') == 'clicked_tov_with_id':
                '''Добавляет в базу данных количество к популярности товара '''
                add_logs(sql, db, 'clicked_tov_with_id')
                sql.execute(f"UPDATE items SET popular=popular+1 WHERE id='{request.data.get('id')}'")
                db.commit()
                return Response()

            elif request.data.get('oper') == 'get_list_by_search':
                '''Добавляет в базу данных количество к популярности товара '''
                if add_oper(request.data.get('mail'), sql, db):
                    return Response({'error': None})
                add_logs(sql, db, 'get_list_by_search')
                ask = request.data.get('ask')
                type = request.data.get('type')
                gen = request.data.get('gen')
                add1, add2, add3 = '', '', ''
                if 'm' in gen:
                    add1 = " AND description NOT LIKE '%Women%' OR description NOT LIKE '%(w)%'"
                if 'w' in gen:
                    add2 = " AND description LIKE '%Women%' OR description LIKE '%(w)%'"
                if 'u' in gen:
                    add3 = " AND description LIKE '%unisex%'"
                cost_min = int(get_uans(int(request.data.get('cost_min')), sql))
                cost_max = int(get_uans(int(request.data.get('cost_max')), sql))
                if ask == '':
                    try:
                        if int(type) == 1:
                            return Response({'ids': sql.execute(
                                f"SELECT id FROM items WHERE price BETWEEN {cost_min} AND {cost_max} {add1} {add2} {add3} ORDER BY price").fetchall()})
                        elif int(type) == -1:
                            return Response({'ids': sql.execute(
                                f"SELECT id FROM items WHERE price BETWEEN {cost_min} AND {cost_max} {add1} {add2} {add3} ORDER BY price DESC").fetchall()})
                        else:
                            return Response(
                                {'ids': sql.execute(
                                    f"SELECT id FROM items WHERE price BETWEEN {cost_min} AND '{cost_max}' {add1} {add2} {add3} ORDER BY popular DESC").fetchall()})
                    except:
                        return Response({'ids': '-1'})
                else:
                    try:
                        if int(type) == 1:
                            asad = sql.execute(
                                f"SELECT id FROM items WHERE description LIKE '%{ask}%' AND price BETWEEN {cost_min} AND {cost_max} {add1} {add2} {add3} ORDER BY price").fetchall()
                            return Response({'ids': '-1' if len(asad) == 0 else asad})
                        elif int(type) == -1:
                            asad = sql.execute(
                                f"SELECT id FROM items WHERE description LIKE '%{ask}%' AND price BETWEEN {cost_min} AND {cost_max} {add1} {add2} {add3} ORDER BY price DESC").fetchall()
                            return Response({'ids': '-1' if len(asad) == 0 else asad})
                        else:
                            asad = sql.execute(
                                f"SELECT id FROM items WHERE description LIKE '%{ask}%' AND price BETWEEN {cost_min} AND {cost_max} {add1} {add2} {add3} ORDER BY popular DESC").fetchall()
                            return Response({'ids': '-1' if len(asad) == 0 else asad})
                    except:
                        return Response({'ids': '-1'})

            elif request.data.get('oper') == 'add_in_busket':
                '''По Id товара, размеру и почте добавляем в локальную БД заказ к пользователю'''
                if add_oper(request.data.get('mail'), sql, db):
                    return Response({'error': None})
                add_logs(sql, db, 'add_in_busket')
                slov = request.data
                tov_id = slov.get('id')
                size_of = slov.get('size')
                mail = slov.get('mail')

                sql.execute(f"INSERT INTO baskets ('mail','tov_id','size') VALUES ('{mail}','{tov_id}','{size_of}')")
                db.commit()
                return Response()

            elif request.data.get('oper') == 'delete_from_busket':
                '''По Id товара, размеру и почте удаляет из локальной БД заказ у пользователя           '''
                if add_oper(request.data.get('mail'), sql, db):
                    return Response({'error': None})
                add_logs(sql, db, 'delete_from_busket')
                slov = request.data
                tov_id = slov.get('id')
                size_of = slov.get('size')
                mail = slov.get('mail')

                sql.execute(f"DELETE FROM baskets WHERE mail='{mail}' AND size='{size_of}' AND tov_id='{tov_id}'")
                db.commit()
                return Response()

            elif request.data.get('oper') == 'get_busket':
                ''' По почте возвращает список id и размера добавленного в корзину товара'''
                if add_oper(request.data.get('mail'), sql, db):
                    return Response({'error': None})
                add_logs(sql, db, 'get_busket')
                mail = request.data.get('mail')

                ans = {'ans': []}
                for info in sql.execute(f"SELECT * FROM baskets WHERE mail='{mail}'").fetchall():
                    ans['ans'].append([info[1], info[2]])
                return Response(ans)


            elif request.data.get('oper') == 'add_like':
                '''Добавляет товар в избранное'''
                if add_oper(request.data.get('mail'), sql, db):
                    return Response({'error': None})
                add_logs(sql, db, 'add_like')
                slov = request.data
                tov_id = slov.get('id')
                mail = slov.get('mail')

                sql.execute(
                    f"INSERT INTO likes ('mail','tov_id','date') VALUES ('{mail}','{tov_id}','{dt.datetime.now()}')")
                db.commit()
                return Response()

            elif request.data.get('oper') == 'is_liked':
                '''добавлен ли товар с таким id в избранное'''
                if add_oper(request.data.get('mail'), sql, db):
                    return Response({'error': None})
                add_logs(sql, db, 'is_liked')
                slov = request.data
                tov_id = slov.get('id')
                mail = slov.get('mail')

                return Response(
                    {'ans': bool(
                        sql.execute(f"SELECT * FROM likes WHERE tov_id='{tov_id}' AND mail='{mail}'").fetchone())})

            elif request.data.get('oper') == 'liked_list':
                '''добавлен ли товар с таким id в избранное'''
                if add_oper(request.data.get('mail'), sql, db):
                    return Response({'error': None})
                add_logs(sql, db, 'liked_list')
                slov = request.data
                mail = slov.get('mail')

                arr = sql.execute(f"SELECT * FROM likes WHERE mail='{mail}'").fetchall()
                tmp = []
                for i in arr:
                    tmp.append(i)
                tmp.sort(key=lambda x: dt.datetime.strptime(str(x[2]), '%Y-%m-%d %H:%M:%S.%f'), reverse=True)
                for i in range(len(tmp)):
                    tmp[i] = tmp[i][1]
                return Response({'ans': tmp})



            elif request.data.get('oper') == 'delete_like':
                '''Удаляет товар из избранного'''
                if add_oper(request.data.get('mail'), sql, db):
                    return Response({'error': None})
                add_logs(sql, db, 'delete_like')
                slov = request.data
                tov_id = int(slov.get('id'))
                mail = slov.get('mail')
                sql.execute(f"DELETE FROM likes WHERE mail='{mail}' AND tov_id='{tov_id}'")
                db.commit()
                return Response()



            elif request.data.get('oper') == 'send_apply_update_password_mail':
                '''Отправляет пользователю сообщение на почту для подтверждения почты'''
                if add_oper(request.data.get('mail'), sql, db):
                    return Response({'error': None})
                add_logs(sql, db, 'send_apply_update_password_mail')
                slov = request.data
                mail = slov.get('mail')
                sql.execute(f"DELETE FROM mail_accept WHERE mail='{mail}'").fetchall()
                code = ''.join(random.choice(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']) for i in range(6))
                sql.execute(f"INSERT INTO mail_accept ('mail','code') VALUES ('{mail}','{code}')")
                db.commit()
                text = f"""Для восстановления пароля аккаунта введите этот код:
    
{code}

Срок действия кода подтверждения истекает через 48 часов.

Если вы не запрашивали этот код, игнорируйте это сообщение.
"""
                smtp_server = smtplib.SMTP("smtp.yandex.ru", 587)
                smtp_server.starttls()
                smtp_server.login("Gidra1231223@yandex.ru", "zaharov20010974")

                # Настройка параметров сообщения
                msg = MIMEMultipart()
                msg["From"] = "Gidra1231223@yandex.ru"
                msg["To"] = mail
                msg["Subject"] = "Восстановление пароля"

                msg.attach(MIMEText(text, "plain"))
                smtp_server.sendmail("Gidra1231223@yandex.ru", mail, msg.as_string())
                return Response({'ans': True})

            elif request.data.get('oper') == 'send_apply_mail':
                '''Отправляет пользователю сообщение на почту для подтверждения почты'''
                if add_oper(request.data.get('mail'), sql, db):
                    return Response({'error': None})
                try:
                    add_logs(sql, db, 'send_apply_mail')
                    slov = request.data
                    mail = slov.get('mail')
                    sql.execute(f"DELETE FROM mail_accept WHERE mail='{mail}'").fetchall()
                    code = ''.join(random.choice(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']) for i in range(6))
                    sql.execute(f"INSERT INTO mail_accept ('mail','code') VALUES ('{mail}','{code}')")
                    db.commit()
                    text = f"""Для подтверждения аккаунта введите этот код:
        
{code}

Срок действия кода подтверждения истекает через 48 часов.

Если вы не запрашивали этот код, игнорируйте это сообщение."""

                    smtp_server = smtplib.SMTP("smtp.yandex.ru", 587)
                    smtp_server.starttls()
                    smtp_server.login("Gidra1231223@yandex.ru", "zaharov20010974")

                    # Настройка параметров сообщения
                    msg = MIMEMultipart()
                    msg["From"] = "Gidra1231223@yandex.ru"
                    msg["To"] = mail
                    msg["Subject"] = "Оповещение"

                    msg.attach(MIMEText(text, "plain"))
                    smtp_server.sendmail("Gidra1231223@yandex.ru", mail, msg.as_string())
                    return Response({'ans': True})
                except Exception as ex:
                    return Response({'er': str(ex)}, 401)

            elif request.data.get('oper') == 'check_correct_mail_code':
                '''Отправляет пользователю сообщение на почту для подтверждения почты'''
                if add_oper(request.data.get('mail'), sql, db):
                    return Response({'error': None})
                add_logs(sql, db, 'check_correct_mail_code')
                slov = request.data
                return Response({'ans': bool(sql.execute(
                    f"SELECT * FROM mail_accept WHERE mail='{slov.get('mail')}' AND code='{slov.get('code')}'").fetchone())})

            elif request.data.get('oper') == 'check_sign_in_user':
                '''Проверяет корректность пароля и почты для входа в ЛК'''
                if add_oper(request.data.get('mail'), sql, db):
                    return Response({'error': None})
                add_logs(sql, db, 'check_sign_in_user')
                slov = request.data
                return Response({'ans': bool(sql.execute(
                    f"SELECT * FROM users WHERE mail='{slov.get('mail')}' AND password='{slov.get('password')}'").fetchone())})

            elif request.data.get('oper') == 'get_account_info_by_mail':
                '''Обновляет пароль для пользователя с почтой mail '''
                if add_oper(request.data.get('mail'), sql, db):
                    return Response({'error': None})
                add_logs(sql, db, 'get_account_info_by_mail')
                a = sql.execute(f"SELECT * FROM users WHERE mail = '{request.data.get('mail')}'").fetchone()
                arr = [0] * len(a)
                for i in range(len(a)):
                    arr[i] = str(a[i])

                return Response(
                    {'name': arr[3], 'surname': arr[4], 'age': arr[5], 'net': arr[6], 'phone': arr[7],
                     'address': arr[8],
                     'postcode': arr[9]})

            elif request.data.get('oper') == 'set_account_info_by_mail':
                '''Записывает всю информацию о аккаунте по названию почты(имя, фамилию, возраст, адрес, вк/тг?? '''
                if add_oper(request.data.get('mail'), sql, db):
                    return Response({'error': None})
                add_logs(sql, db, 'set_account_info_by_mail')
                sql.execute(
                    f"UPDATE users SET name='{request.data.get('name')}' WHERE mail='{request.data.get('mail')}'")
                sql.execute(
                    f"UPDATE users SET surname='{request.data.get('surname')}' WHERE mail='{request.data.get('mail')}'")
                sql.execute(f"UPDATE users SET age='{request.data.get('age')}' WHERE mail='{request.data.get('mail')}'")
                sql.execute(f"UPDATE users SET net='{request.data.get('net')}' WHERE mail='{request.data.get('mail')}'")
                sql.execute(
                    f"UPDATE users SET phone='{request.data.get('phone')}' WHERE mail='{request.data.get('mail')}'")
                sql.execute(
                    f"UPDATE users SET address='{request.data.get('address')}' WHERE mail='{request.data.get('mail')}'")
                sql.execute(
                    f"UPDATE users SET postcode='{request.data.get('postcode')}' WHERE mail='{request.data.get('mail')}'")
                db.commit()
                return Response()


            elif request.data.get('oper') == 'create_order':
                '''Отправляет все данные о пользователе и о заказе на сервер, присваивая ему номер'''
                if add_oper(request.data.get('mail'), sql, db):
                    return Response({'error': None})
                add_logs(sql, db, 'create_order')
                slov = request.data
                mail = slov.get('mail')
                arr = sql.execute(f"SELECT * FROM baskets WHERE mail='{mail}'").fetchall()
                basket = []
                for i in arr:
                    basket.append(':'.join((i[1], i[2])))
                basket = ';'.join(basket)
                sql.execute(f"DELETE FROM 'baskets' WHERE mail='{mail}'")
                sql.execute(
                    f"INSERT INTO orders ('mail','name','surname','net','phone','address','postcode','basket','date','status') VALUES ('{slov.get('mail')}','{slov.get('name')}',"
                    f"'{slov.get('surname')}','{slov.get('net')}','{slov.get('phone')}','{slov.get('address')}','{slov.get('postcode')}','{basket}','{dt.datetime.today()}','wait')")
                db.commit()
                text = f"""
ВНИМАНИЕ, НОВЫЙ ЗАКАЗ ОТ чевелока с номером телефона {slov['phone']}
    
"""
                for i in admins:
                    requests.post(f'https://api.telegram.org/bot{TOK}/sendMessage?chat_id={i}&text={text}')

                return Response({'num': len(sql.execute(f"SELECT * FROM orders").fetchall())})

            elif request.data.get('oper') == 'get_order_by_num':
                '''Запрашивает все данные о заказе по его номеру: массив товаров и размеров, адрес, дата'''
                add_logs(sql, db, 'get_order_by_num')
                slov = request.data
                arr = sql.execute(f"SELECT * FROM orders WHERE id='{slov.get('num')}'").fetchone()
                busket = arr[8].split(';')
                bsk = []
                for i in busket:
                    bsk.append(i.split(':'))
                s = 0
                for i in bsk:
                    tov_id, size = i
                    sz = sql.execute(f"SELECT * FROM sizes WHERE id='{tov_id}'").fetchone()[1].split(';')
                    for j in sz:
                        a, b = j.split(',')
                        if a == size:
                            s += int(get_cost(int(b), sql).replace(' ', ''))
                return Response(
                    {'mail': arr[1], 'name': arr[2], 'phone': arr[5], 'address': arr[6],
                     'postcode': arr[7], 'date': arr[9], 'status': arr[10], 'busket': bsk, 'sum': s})


            elif request.data.get('oper') == 'get_order_story':
                '''Запрашивает историю заказов по почте'''
                if add_oper(request.data.get('mail'), sql, db):
                    return Response({'error': None})
                add_logs(sql, db, 'get_order_story')
                slov = request.data
                arr = sql.execute(f"SELECT * FROM orders WHERE mail='{slov.get('mail')}'").fetchall()
                return Response({'nums': [i[0] for i in arr]})
    elif request.method == 'GET':
        return Response({'data': str(request)})
