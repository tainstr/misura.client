def convert(template, substitutions_hash, tag='$'):
	output = template

	for key in substitutions_hash:
		output = output.replace(key, substitutions_hash[key])

	return output