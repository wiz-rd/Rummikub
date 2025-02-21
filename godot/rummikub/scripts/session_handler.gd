extends Node

var username: String
var server_url: String = "http://127.0.0.1"
var port: int = 8000
var api_string: String = "/api"
# TODO:
# This will have to be updated to remove the port
# once the site is published externally
var api_url: String = server_url + ":" + str(port) + api_string


func create_username(usrnm: String):
	"""
	Creates a username on the server.
	"""
	# using a CookieHTTPRequest instead of a
	# standard HTTPRequest SHOULD store the
	# cookies automatically
	var req = CookieHTTPRequest.new()
	add_child(req)

	# TODO: delete debugging
	var full_url = api_url + "/user/" + usrnm
	print(full_url)

	req.request_completed.connect(_on_create_username)
	var error = req.cookie_request(
		# the username is set based on the URL
		full_url,
		# no special headers are needed
		[],
		# put the username
		HTTPClient.Method.METHOD_PUT
	)
	if error != OK:
		push_error("Error in setting username.")


func get_username():
	"""
	Updates the username value to what the server has
	stored as their username.
	"""
	var req = CookieHTTPRequest.new()
	add_child(req)

	# TODO: delete debugging
	var full_url = api_url + "/user"
	print(full_url)

	req.request_completed.connect(_on_get_username)
	var error = req.cookie_request(full_url)
		## the username is set based on the URL
		#full_url,
		## no special headers are needed
		#[""],
		## get the username
		#HTTPClient.Method.METHOD_GET
	#)
	if error != OK:
		push_error("Error in getting username.")


func _on_create_username(_result, response_code, _headers, body):
	"""
	Attempts to create a username for the given user.
	"""
	print(response_code)
	if response_code != HTTPClient.RESPONSE_OK:
		# CRITICAL TODO: Notify the user in some way
		print("The username creation failed. Reasoning:")
		print(body.get_string_from_utf8())


func _on_get_username(_result, response_code, _headers, body):
	"""
	Performs the updating of the username value.
	"""
	print(_headers)
	print("body: " + body.get_string_from_utf8())
	if response_code != HTTPClient.RESPONSE_OK:
		push_error("There was an error obtaining the username.")
		# CRITICAL TODO: Notify the user if this fails
	else:
		var json = JSON.new()
		json.parse(body.get_string_from_utf8())
		var response = json.get_data()
		# update the global username value
		username = response["username"]
