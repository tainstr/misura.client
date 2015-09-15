import base64

def embed(data, type):
	encoded_data = base64.b64encode(data)
	return "<img src='data:image/%s;base64,%s' alt=''>" % (type, encoded_data)

def table_from(images, type='gif', images_per_line=5):
	html = "<table><tr>"

	for index, image in enumerate(images):
		html = html + "<td>%s</td>" % embed(image, type)
		if (index + 1) % images_per_line == 0:
			html = html + "</tr><tr>"

	return html + "</tr></table>"