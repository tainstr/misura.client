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
               jobs=lambda *x, **k: None,
               job=lambda *x, **k: None,
               done=lambda *x, **k: None,
               check_abort=lambda: False,
               do_abort=lambda: False):
        
        jobs(len(images), 'Adding images', abort=do_abort)
        html = "<table><tr>"
        labels = {}
        for name, temp in characteristic_temperatures.items():
                labels[temp] = name 
                
        Tpre = -3000
        for i, image in enumerate(images):
                if check_abort():
                    logging.debug('Export aborted')
                    done('Adding images')
                    return False
                job(i, 'Adding images')
                
                T=image[2]
                Tnext = T+3000
                label = ''
                if i<len(images)-1:
                    Tnext = images[i+1][2]
                    
                label = get_label(Tpre, T, Tnext, labels) + '<br/><br/>'

                html = html + "<td>%s</td>" % embed_with_labels(image[0],
                                                                image[1],
                                                                image[2],
                                                                image[3],
                                                                type,
                                                                label)
                if (i + 1) % images_per_line == 0:
                        html = html + "</tr><tr>"
                
                Tpre = image[2]
        done('Adding images')
        return html + "</tr></table>"

def encode_image(image_file_name):
    return encode(open(image_file_name).read())

def get_label(Tpre, T, Tnext, labels):
    for LT, name in labels.items():
        dt=abs(T-LT)
        if abs(T-Tpre)>dt and abs(Tnext-T)>dt:
            return labels.pop(LT)
    return ''
    