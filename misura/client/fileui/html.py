#!/usr/bin/python
# -*- coding: utf-8 -*-

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
               sintering_temp=None,
               softening_temp=None,
               sphere_temp=None,
               half_sphere_temp=None,
               melting_temp=None):

        html = "<table><tr>"
        for index, image in enumerate(images):
                label = '&nbsp;'
                current_image_temperature = int(image[2])
                if sintering_temp == current_image_temperature:
                        label = 'Sintering'
                if softening_temp == current_image_temperature:
                        label = "Softening"
                if sphere_temp == current_image_temperature:
                        label = 'Sphere'
                if half_sphere_temp == current_image_temperature:
                        label = 'Half Sphere'
                if melting_temp == current_image_temperature:
                        label = 'Melting'

                html = html + "<td>%s</td>" % embed_with_labels(image[0],
                                                                image[1],
                                                                image[2],
                                                                image[3],
                                                                type,
                                                                label)
                if (index + 1) % images_per_line == 0:
                        html = html + "</tr><tr>"

        return html + "</tr></table>"

def encode_image(image_file_name):
	return encode(open(image_file_name).read())
