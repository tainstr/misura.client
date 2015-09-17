from misura.client.fileui import html
from misura.client.fileui import template
from PyQt4 import QtGui, QtCore
from ...canon import csutil

def create(decoder, measure, time_data, temperature_data, template_filename, logo_filename):
    template_text = open(template_filename).read()

    image_file_contents = open(logo_filename).read()
    base64_logo = html.encode(image_file_contents)

    total_number_of_images = len(decoder)
    all_images_data = []
    last_temperature = -100
    image_count = 1
    for i in range(total_number_of_images):
        time, qimage = decoder.get_data(i)
        image_number = i + 1
        temperature_index = csutil.find_nearest_val(time_data, time)
        image_temperature = int(temperature_data[temperature_index])

        if abs(last_temperature - int(image_temperature)) >= 1:
            image_data = byte_array_from(qimage)
            all_images_data.append([image_data, image_count, image_temperature, csutil.from_seconds_to_hms(int(time))])
            last_temperature = image_temperature
            image_count += 1

    images_table_html = html.table_from(all_images_data, 'png')

    substitutions_hash = {"$LOGO$": base64_logo,
                          "$code$": measure['uid'],
                          "$title$": measure['name'],
                          "$date$": measure['date'],
                          "$IMAGES_TABLE$": images_table_html }

    return template.convert(template_text, substitutions_hash)


def byte_array_from(qimage):
    image_data = QtCore.QByteArray()
    buffer = QtCore.QBuffer(image_data)
    buffer.open(QtCore.QIODevice.WriteOnly)
    qimage.save(buffer, 'PNG')
    buffer.close()

    return image_data

