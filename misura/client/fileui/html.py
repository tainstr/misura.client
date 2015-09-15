import base64

def embed(data, type):
	encoded_data = base64.b64encode(data)
	return "<img src='data:image/%s;base64,%s' alt=''>" % (type, encoded_data)