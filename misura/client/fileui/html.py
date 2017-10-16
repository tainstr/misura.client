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
                      temperature,
                      time,
                      type='gif',
                      characteristic_shape_label = '',
                      shape_anchor='',
                      T_anchor=''):
        image_html = embed(data, type)
        shape_label = "<b>{}</b>".format(characteristic_shape_label)
        if shape_anchor:
            shape_label = "<a name='{}'>{}</a>".format(shape_anchor,shape_label)
        T_label = "{}&deg;C".format(temperature)
        if T_anchor:
            T_label = "<a name='{}'>{}</a>".format(T_anchor, T_label)
                  
        return "<table><tr><td align='center'>{}</td></tr>\
<tr><td>{}</td></tr><tr>\
<td><div class='temperature'>{}</div><div class='time'>{}</div></td>\
</tr></table>".format(shape_label,
                image_html, 
                T_label,
                time)

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
        shape_anchors = []
        T_anchors = []
        step = int(len(images)/10)
        for i, image in enumerate(images):
                if check_abort():
                    logging.debug('Export aborted')
                    done('Adding images')
                    return False
                job(i, 'Adding images')
                
                T=image[2]
                Tr = round(T,1)
                Tnext = T+3000
                label = ''
                if i<len(images)-1:
                    Tnext = images[i+1][2]
                    
                label = get_label(Tpre, T, Tnext, labels)
                shape_anchor = label.replace(' ', '')
                if label:
                    shape_anchors.append('<a href="#{}">{}</a>'.format(shape_anchor, label))
                label += '<br/><br/>'
                
                T_anchor = ''
                if i%step==0:
                    T_anchor = Tr
                    T_anchors.append('<a href="#{}">{}</a>'.format(T_anchor,T_anchor))
                
                html = html + "<td>%s</td>" % embed_with_labels(image[0],
                                                                Tr,
                                                                image[3],
                                                                type,
                                                                label, 
                                                                shape_anchor,
                                                                T_anchor)
                
                if (i + 1) % images_per_line == 0:
                        html = html + "</tr><tr>"
                html += "\n"
                Tpre = image[2]
                
        # Add floating menu
        menu = '<div id="menu" class="no-print">' + '<br/>'.join(shape_anchors+T_anchors)
        html += menu + '</div>'
        
        done('Adding images')
        return html + "</tr></table>"

def encode_image(image_file_name):
    return encode(open(image_file_name).read())

def get_label(Tpre, T, Tnext, labels):
    for LT, name in labels.items():
        if LT is None:
            continue
        dt=abs(T-LT)
        if abs(T-Tpre)>dt and abs(Tnext-T)>dt:
            return labels.pop(LT)
    return ''
    