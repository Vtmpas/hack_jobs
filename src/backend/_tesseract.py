
# brew install tesseract
# brew install poppler
# pip install PyPDF2 pytesseract pdfminer.six pdfplumber pdf2image Pillow

# Для считывания PDF
import PyPDF2
# Для анализа структуры PDF и извлечения текста
from pdfminer.high_level import extract_pages, extract_text
from pdfminer.layout import LTTextContainer, LTChar, LTRect, LTFigure
# Для извлечения текста из таблиц в PDF
import pdfplumber
# Для извлечения изображений из PDF
from PIL import Image
from pdf2image import convert_from_path
# Для выполнения OCR, чтобы извлекать тексты из изображений 
import pytesseract 
# Для удаления дополнительно созданных файлов
import os


def text_extraction(element):
    # Извлекаем текст из вложенного текстового элемента
    line_text = element.get_text()
    
    # Находим форматы текста
    # Инициализируем список со всеми форматами, встречающимися в строке текста
    line_formats = []
    for text_line in element:
        if isinstance(text_line, LTTextContainer):
            # Итеративно обходим каждый символ в строке текста
            for character in text_line:
                if isinstance(character, LTChar):
                    # Добавляем к символу название шрифта
                    line_formats.append(character.fontname)
                    # Добавляем к символу размер шрифта
                    line_formats.append(character.size)
    # Находим уникальные размеры и названия шрифтов в строке
    format_per_line = list(set(line_formats))
    
    # Возвращаем кортеж с текстом в каждой строке вместе с его форматом
    return (line_text, format_per_line)

# Создаём функцию для вырезания элементов изображений из PDF
def crop_image(element, pageObj):
    # Получаем координаты для вырезания изображения из PDF
    [image_left, image_top, image_right, image_bottom] = [element.x0,element.y0,element.x1,element.y1] 
    # Обрезаем страницу по координатам (left, bottom, right, top)
    pageObj.mediabox.lower_left = (image_left, image_bottom)
    pageObj.mediabox.upper_right = (image_right, image_top)
    # Сохраняем обрезанную страницу в новый PDF
    cropped_pdf_writer = PyPDF2.PdfWriter()
    cropped_pdf_writer.add_page(pageObj)
    # Сохраняем обрезанный PDF в новый файл
    with open('cropped_image.pdf', 'wb') as cropped_pdf_file:
        cropped_pdf_writer.write(cropped_pdf_file)

# Создаём функцию для преобразования PDF в изображения
def convert_to_images(input_file,):
    images = convert_from_path(input_file)
    image = images[0]
    output_file = "PDF_image.png"
    image.save(output_file, "PNG")

# Создаём функцию для считывания текста из изображений
def image_to_text(image_path):
    # Считываем изображение
    img = Image.open(image_path)
    # Извлекаем текст из изображения
    text = pytesseract.image_to_string(img, lang='rus')
    return text


# Извлечение таблиц из страницы

def extract_table(pdf_path, page_num, table_num):
    # Открываем файл pdf
    pdf = pdfplumber.open(pdf_path)
    # Находим исследуемую страницу
    table_page = pdf.pages[page_num]
    # Извлекаем соответствующую таблицу
    table = table_page.extract_tables()[table_num]
    return table

# Преобразуем таблицу в соответствующий формат
def table_converter(table):
    table_string = ''
    # Итеративно обходим каждую строку в таблице
    for row_num in range(len(table)):
        row = table[row_num]
        # Удаляем разрыв строки из текста с переносом
        cleaned_row = [item.replace('\n', ' ') if item is not None and '\n' in item else 'None' if item is None else item for item in row]
        # Преобразуем таблицу в строку
        table_string+=('|'+'|'.join(cleaned_row)+'|'+'\n')
    # Удаляем последний разрыв строки
    table_string = table_string[:-1]
    return table_string


def pdf_parser(pdf_path):
    # Находим путь к PDF
    # pdf_path = 'ИИ-Мосбиржа.pdf'
    # pdf_path = 'kotovo-hh-ru-vacan....pdf'
    # pdf_path = 'Researh Data Scientist (smolt quality project).pdf'
    # pdf_path = "TWork_вакансия_онбординг_и_обучение.pdf"

    # создаём объект файла PDF
    pdfFileObj = open(pdf_path, 'rb')
    # создаём объект считывателя PDF
    pdfReaded = PyPDF2.PdfReader(pdfFileObj)

    # Создаём словарь для извлечения текста из каждого изображения
    text_per_page = {}
    # Извлекаем страницы из PDF
    for pagenum, page in enumerate(extract_pages(pdf_path)):
        
        # Инициализируем переменные, необходимые для извлечения текста со страницы
        pageObj = pdfReaded.pages[pagenum]
        page_text = []
        line_format = []
        text_from_images = []
        text_from_tables = []
        page_content = []
        # Инициализируем количество исследованных таблиц
        table_num = 0
        first_element= True
        table_extraction_flag= False
        # Открываем файл pdf
        pdf = pdfplumber.open(pdf_path)
        # Находим исследуемую страницу
        page_tables = pdf.pages[pagenum]
        # Находим количество таблиц на странице
        tables = page_tables.find_tables()


        # Находим все элементы
        page_elements = [(element.y1, element) for element in page._objs]
        # Сортируем все элементы по порядку нахождения на странице
        page_elements.sort(key=lambda a: a[0], reverse=True)

        # Находим элементы, составляющие страницу
        for i,component in enumerate(page_elements):
            # Извлекаем положение верхнего края элемента в PDF
            pos= component[0]
            # Извлекаем элемент структуры страницы
            element = component[1]
            
            # Проверяем, является ли элемент текстовым
            if isinstance(element, LTTextContainer):
                # Проверяем, находится ли текст в таблице
                if table_extraction_flag == False:
                    # Используем функцию извлечения текста и формата для каждого текстового элемента
                    (line_text, format_per_line) = text_extraction(element)
                    # Добавляем текст каждой строки к тексту страницы
                    page_text.append(line_text)
                    # Добавляем формат каждой строки, содержащей текст
                    line_format.append(format_per_line)
                    page_content.append(line_text)
                else:
                    # Пропускаем текст, находящийся в таблице
                    pass

            # Проверяем элементы на наличие изображений
            if isinstance(element, LTFigure):
                # Вырезаем изображение из PDF
                crop_image(element, pageObj)
                # Преобразуем обрезанный pdf в изображение
                convert_to_images('cropped_image.pdf')
                # Извлекаем текст из изображения
                image_text = image_to_text('PDF_image.png')
                text_from_images.append(image_text)
                page_content.append(image_text)
                # Добавляем условное обозначение в списки текста и формата
                page_text.append('image')
                line_format.append('image')

            # Проверяем элементы на наличие таблиц
            if isinstance(element, LTRect):
                # Если первый прямоугольный элемент
                if first_element == True and (table_num+1) <= len(tables):
                    # Находим ограничивающий прямоугольник таблицы
                    lower_side = page.bbox[3] - tables[table_num].bbox[3]
                    upper_side = element.y1 
                    # Извлекаем информацию из таблицы
                    table = extract_table(pdf_path, pagenum, table_num)
                    # Преобразуем информацию таблицы в формат структурированной строки
                    table_string = table_converter(table)
                    # Добавляем строку таблицы в список
                    text_from_tables.append(table_string)
                    page_content.append(table_string)
                    # Устанавливаем флаг True, чтобы избежать повторения содержимого
                    table_extraction_flag = True
                    # Преобразуем в другой элемент
                    first_element = False
                    # Добавляем условное обозначение в списки текста и формата
                    page_text.append('table')
                    line_format.append('table')

                # Проверяем, извлекли ли мы уже таблицы из этой страницы
                if element.y0 >= lower_side and element.y1 <= upper_side:
                    pass
                elif not isinstance(page_elements[i+1][1], LTRect):
                    table_extraction_flag = False
                    first_element = True
                    table_num+=1


        # Создаём ключ для словаря
        dctkey = 'Page_'+str(pagenum)
        # Добавляем список списков как значение ключа страницы
        text_per_page[dctkey]= [page_text, line_format, text_from_images,text_from_tables, page_content]

    # Закрываем объект файла pdf
    pdfFileObj.close()

    # Удаляем созданные дополнительные файлы
    # os.remove('cropped_image.pdf')
    # os.remove('PDF_image.png')

    # Удаляем содержимое страницы


    # result = ''.join(text_per_page['Page_0'][4])
    result = ''.join(str(text_per_page[x][4]) for x in text_per_page)
    return result


if __name__ == "__main__":
    # print(pdf_parser('kotovo-hh-ru-vacan....pdf'))
    # print(pdf_parser("TWork_вакансия_онбординг_и_обучение.pdf"))
    print(pdf_parser("Researh Data Scientist (smolt quality project).pdf"))
    
    