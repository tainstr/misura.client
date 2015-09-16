import base64

def encode(data):
	return base64.b64encode(data)

def embed(data, type):
	return "<img src='data:image/%s;base64,%s' alt=''>" % (type, encode(data))

def embed_with_labels(data, image_number, temperature, time, type='gif'):
	image_html = embed(data, type)
	return "<table><tr><td>%s</td></tr><tr><td><b>%s</b></td></tr><tr><td>%s&deg;C</td></tr><tr><td>%s</td></tr></table>" % (image_html, image_number, temperature, time)

def table_from(images, type='gif', images_per_line=5):
	html = "<table><tr>"

	for index, image in enumerate(images):
		html = html + "<td>%s</td>" % embed_with_labels(image[0], image[1], image[2], image[3], type)
		if (index + 1) % images_per_line == 0:
			html = html + "</tr><tr>"

	return html + "</tr></table>"

def encode_image(image_file_name):
	return encode(open(image_file_name).read())