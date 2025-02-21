extends Node

const server_url: String = "http://127.0.0.1"
const api_string: String = "/api"
var port: int = 8000
var username: String

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

	var full_url = api_url + "/user/" + usrnm

	req.request_completed.connect(_on_create_username)
	var error = req.cookie_request(
		# the username is set based on the URL
		full_url,
		# no special headers are needed
		HTTPCookieStore._retrieve_cookies_for_header(server_url),
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

	var full_url = api_url + "/user"

	var session_id = HTTPCookieStore.get_cookie_header_for_request(server_url)
	if session_id == null:
		session_id = HTTPCookieStore._retrieve_cookies_for_header(server_url)

	req.request_completed.connect(_on_get_username)
	var error = req.cookie_request(
		# the URL
		full_url,
		# the cookies, because I have to pass an argument here
		session_id,
		# get the username
		HTTPClient.Method.METHOD_GET
	)
	if error != OK:
		push_error("Error in getting username.")


func _on_create_username(_result, response_code, _headers, body):
	"""
	Attempts to create a username for the given user.
	"""
	if response_code != HTTPClient.RESPONSE_OK:
		# CRITICAL TODO: Notify the user in some way
		print(body.get_string_from_utf8())
		push_error("The username creation failed. Reasoning:")


func _on_get_username(_result, response_code, _headers, body):
	"""
	Performs the updating of the username value.
	"""
	if response_code != HTTPClient.RESPONSE_OK:
		push_error("There was an error obtaining the username.")
		# CRITICAL TODO: Notify the user if this fails
	else:
		var json = JSON.new()
		json.parse(body.get_string_from_utf8())
		var response = json.get_data()
		# update the global username value
		username = response["username"]
