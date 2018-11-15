#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import base64
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from misura.client.fileui import html
from misura.client.fileui import template

from PyQt4 import QtGui, QtCore
from ...canon import csutil


def create_images_report(decoder,
                         measure,
                         characteristic_shapes,
                         output = False,
                         startTemp=0,
                         step=1,
                         timeStep=0,
                         jobs=lambda *x, **k: None,
                         job=lambda *x, **k: None,
                         done=lambda *x, **k: None,
                         check_abort=lambda: False,
                         do_abort=lambda: 0):
    Tpath = decoder.datapath.split('/')
    Tpath[-1]='T'
    Tpath = '/'.join(Tpath)
    # Get index of startTemp in sample/T dataset
    idx0, t0, T0 = decoder.proxy.rises(Tpath, startTemp)
    # Get index of start time in sample/profile
    idx0 = decoder.get_time(t0)
    total_number_of_images = len(decoder)
    all_images_data = []
    image_count = 1
    jobs(3, 'Creating images report', abort=do_abort)
    jobs(total_number_of_images-idx0+1, 'Decoding', abort=do_abort)
    v = range(idx0, total_number_of_images)
    if idx0!=0:
        v=[0]+v
    last_temperature = int(T0)
    last_time = t0
    i=0
    i0=-1
    time=0
    step_sign=1
    # Always take most frequent, non-zero criteria
    # between step and timeStep
    while i<total_number_of_images:
        if check_abort():
            logging.debug('Export aborted')
            done('Decoding')
            return False
        
        if image_count>1:
            if step>0:
                last_temperature+=step_sign*step
                i, nt, nT = decoder.proxy.nearest(Tpath, last_temperature)
                print 'new T', i, nt, nT
                # If going backward, try inverting the time
                if nt<=time:
                    step_sign*=-1
                    logging.debug('Inverted step sign:', step_sign)
                    last_temperature+=2*step_sign*step
                    i, nt, nT = decoder.proxy.nearest(Tpath, last_temperature)
                    # If time is still backward, means there are no more points
                    if nt<=time:
                        logging.debug('End decoding: no more increments')
                        break
            # Enforce minimum timeStep requirement
            if nt-last_time<timeStep:
                nt = last_time+timeStep
            # Get actual image index
            i = decoder.get_time(nt)
            
        if i<=i0:
            logging.debug('No more images', i0, i)
            break
        time, qimage = decoder.get_data(i)
        last_time = time
        i0=i

        nt, image_temperature = decoder.proxy.col_at_time(Tpath, time, True)
        image_data = byte_array_from(qimage)
        all_images_data.append([image_data,
                                image_count,
                                image_temperature,
                                csutil.from_seconds_to_hms(int(time))])
        image_count += 1
        
        job(i-idx0, 'Decoding')
    done('Decoding')
    job(2, 'Creating images report', 'Creating report structure')
    characteristic_temperatures = {}

    for shape in characteristic_shapes.keys():
        characteristic_temperatures[shape] = float_or_none(characteristic_shapes[shape]['temp'])

    images_table_html = html.table_from(all_images_data,
                                        'png',
                                        5,
                                        characteristic_temperatures,
                                        jobs,
                                        job,
                                        done,
                                        check_abort,
                                        do_abort)
    if images_table_html is False:
        return False
    substitutions_hash = {"$LOGO$": base64_logo(),
                          "$code$": measure['uid'],
                          "$title$": measure['name'],
                          "$date$": measure['date'],
                          "$IMAGES_TABLE$": images_table_html }
    
    job(2, 'Creating images report', 'Writing report to ' + str(output))
    output_html = template.convert(images_template_text(), substitutions_hash)
    if output:
        r = False
        if not output.lower().endswith('.html'):
            output += '.html'
        with open(output, 'w') as output_file:
            output_file.write(output_html)
            r = True
    else:
        r = output_html
    done('Creating images report')
    return r

def float_or_none(float_or_none_string):
    if float_or_none_string == 'None':
        return None
    return float_or_none_string

def byte_array_from(qimage):
    image_data = QtCore.QByteArray()
    buffer = QtCore.QBuffer(image_data)
    buffer.open(QtCore.QIODevice.WriteOnly)
    qimage.save(buffer, 'PNG')
    buffer.close()

    return image_data

def base64_logo():
    from misura.client.clientconf import confdb
    from misura.client import parameters as params
    logo = confdb['rule_logo']
    if not os.path.exists(logo):
        return open(os.path.join(params.pathArt, 'logo.base64'),'rb').read()
    return base64.b64encode(open(logo,'rb').read())
        

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

            td b {
                color: blue;
            }

            .temperature {
                display: inline-block;
            }

            .time {
                float: right;
                margin-right: 0px;
                font-weight: bold;
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
            #menu {
              position: fixed;
              right: 10px;
              top: 10px;
              width: 8em;
            }
            #menu {
              overflow: hidden;
              background-color: #002d62;
            }
            
            #menu a {
              float: left;
              display: block;
              color: #f2f2f2;
              text-align: center;
              padding: 14px 16px;
              text-decoration: none;
              font-size: 17px;
            }
            
            #menu a:hover {
              background-color: #0297d7;
              color: black;
            }

            @media print
            {    
                .no-print, .no-print *
                {
                    display: none !important;
                }
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
