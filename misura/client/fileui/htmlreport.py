#!/usr/bin/python
# -*- coding: utf-8 -*-

from misura.client.fileui import html
from misura.client.fileui import template
from PyQt4 import QtGui, QtCore
from ...canon import csutil, reference

def create_images_report(decoder,
                         measure,
                         time_data,
                         temperature_data,
                         characteristic_shapes,
                         standard='Misura4',
                         output = False,
                         startTemp=0,
                         step=1,
                         jobs=lambda *x: None,
                         job=lambda *x: None,
                         done=lambda *x: None):
    Tpath = decoder.datapath.split('/')
    Tpath[-1]='T'
    Tpath = '/'.join(Tpath)
    # Get index of startTemp in sample/T dataset
    idx0, t0, T0 = decoder.proxy.rises(Tpath, startTemp)
    # Get index of start time in sample/profile
    #idx0 = decoder.proxy.get_time(decoder.datapath, t0)
    idx0 = decoder.get_time(t0)
    total_number_of_images = len(decoder)
    all_images_data = []
    last_temperature = -100
    image_count = 1
    jobs(3, 'Creating images report')
    print 'UUUUUUUUU',total_number_of_images, idx0, step, (total_number_of_images-idx0+1)/step
    jobs((total_number_of_images-idx0+1)/step, 'Decoding')
    v = range(idx0, total_number_of_images)
    if idx0!=0:
        v=[0]+v
    for i in v:
        time, qimage = decoder.get_data(i)
        image_number = i + 1
        image_temperature = decoder.proxy.col_at_time(Tpath, time, True)[1]
        # Take first image then discard anything until startTemp
        if image_temperature<startTemp and image_count==2:
            continue
        if abs(last_temperature - int(image_temperature)) >= step:
            image_data = byte_array_from(qimage)
            all_images_data.append([image_data,
                                    image_count,
                                    image_temperature,
                                    csutil.from_seconds_to_hms(int(time))])
            last_temperature = image_temperature
            image_count += 1
        job(i-idx0, 'Decoding')
    done('Decoding')
    job(1, 'Creating images report', 'Creating report structure')
    characteristic_temperatures = {}

    for shape in characteristic_shapes.keys():
        characteristic_temperatures[shape] = to_int(characteristic_shapes[shape]['temp'])

    images_table_html = html.table_from(all_images_data,
                                        'png',
                                        5,
                                        characteristic_temperatures,
                                        jobs,
                                        job,
                                        done)

    substitutions_hash = {"$LOGO$": base64_logo(),
                          "$code$": measure['uid'],
                          "$title$": measure['name'],
                          "$date$": measure['date'],
                          "$IMAGES_TABLE$": images_table_html }
    
    job(2, 'Creating images report', 'Writing report to' + output)
    output_html = template.convert(images_template_text(), substitutions_hash)
    with open(output, 'w') as output_file:
        output_file.write(output_html)
    done('Creating images report')
    return True

def to_int(float_or_none_string):
    if float_or_none_string == 'None':
        return None
    return int(float_or_none_string)

def byte_array_from(qimage):
    image_data = QtCore.QByteArray()
    buffer = QtCore.QBuffer(image_data)
    buffer.open(QtCore.QIODevice.WriteOnly)
    qimage.save(buffer, 'PNG')
    buffer.close()

    return image_data

def base64_logo():
    return "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"

def images_template_text():
    return """
<html>
    <head>
        <style>
            body {
                background-color: white;
            }

            h1 {
                color: maroon;
            }
            h2 {
                color: black;
            }
            .title {
                vertical-align:middle;
                text-align: center;
                display: inline-block;
            }
            .logo {
                padding: 5%;
                display: inline-block;
            }
            .summary{
                padding: 2%;
                line-height: 200%;
            }
            table{
                margin: 10px;
            }
            table img{
                width: 150px;
            }

            td.number {
                text-align: center;
                font-weight: bold;
            }

            td b {
                color: blue;
            }

            .temperature {
                display: inline-block;
            }

            .time {
                float: right;
                margin-right: 0px;
            }

            a:link {
                color: #555;
                text-decoration: none;
            }

            a:visited {
                color: #555;
                text-decoration: none;
            }

            a:hover {
                color: #000;
                text-decoration: underline;
            }

            a:active {
                color: #555;
                text-decoration: underline;
            }
        </style>
    </head>

    <body>
        <div>
            <div class='title-container'>
                <div class='logo'>
                    <img align=\"center\" src=\"data:image/jpg;base64,$LOGO$\" width=\"200\" alt=\"TA logo\">
                </div>
                <div class='title'>
                    <h2>Heating Microscope</h2>
                    <h1>Misura 4</h1>
                    <p>
                        <small><a href=\"http://www.tainstruments.com\">www.tainstruments.com</a></small><br/>
                    </p>
                </div>
            </div>

            <div class='summary'>
                <div><strong>Code</strong>: $code$</div>
                <div><strong>Title</strong>: $title$</div>
                <div><strong>Date</strong>: $date$</div>
            </div>

            $IMAGES_TABLE$

        </div>
    </body>
</html>
"""
