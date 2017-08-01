#!/usr/bin/python
# -*- coding: utf-8 -*-
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
import base64

def encode(data):
    return base64.b64encode(data)

def embed(data, type):
    return "<img src='data:image/%s;base64,%s' alt=''>" % (type, encode(data))

def embed_with_labels(data,
                      image_number,
                      temperature,
                      time,
                      type='gif',
                      characteristic_shape_label = ''):
        image_html = embed(data, type)
        return "<table><tr><td align='center'><b>%s</b></td></tr><tr><td>%s</td></tr><tr>\
<td class='number'>%s</td></tr><tr>\
<td><div class='temperature'>%s&deg;C</div><div class='time'>%s</div></td>\
</tr></table>" % (characteristic_shape_label, image_html, image_number, temperature, time)

def table_from(images,
               type='gif',
               images_per_line=5,
               characteristic_temperatures={},
               jobs=lambda *x: None,
               job=lambda *x: None,
               done=lambda *x: None,
               check_abort=lambda: False,
               do_abort=lambda: False):
        
        jobs(len(images), 'Adding images', abort=do_abort)
        html = "<table><tr>"
        labels = {}
        for key in characteristic_temperatures.keys():
                labels[characteristic_temperatures[key]] = key + '<br/><br/'

        for index, image in enumerate(images):
                if check_abort():
                    logging.debug('Export aborted')
                    done('Adding images')
                    return False
                job(index, 'Adding images')

                current_image_temperature = int(image[2])

                label = labels.get(current_image_temperature, '<br/><br/>')

                html = html + "<td>%s</td>" % embed_with_labels(image[0],
                                                                image[1],
                                                                image[2],
                                                                image[3],
                                                                type,
                                                                label)
                if (index + 1) % images_per_line == 0:
                        html = html + "</tr><tr>"
        done('Adding images')
        return html + "</tr></table>"

def encode_image(image_file_name):
    return encode(open(image_file_name).read())
