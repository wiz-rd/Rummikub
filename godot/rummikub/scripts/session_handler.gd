extends Node

var username: String
var server_url: String = "localhost"
var port: int = 8000
var api_string: String = "/api"
# TODO:
# This will have to be updated to remove the port
# once the site is published externally
var api_url: String = server_url + ":" + str(port) + api_string


func create_username(username: String):
	"""
	Creates a username on the server.
	"""
	# using a CookieHTTPRequest instead of a
	# standard HTTPRequest SHOULD store the
	# cookies automatically
	var req := CookieHTTPRequest.new()
	req.cookie_request(
		# the username is set based on the URL
		api_url + "/user/" + username,
		# no special headers are needed
		[""],
		# put the username
		HTTPClient.Method.METHOD_PUT
	)


func get_username():
	"""
	Updates the username value to what the server has
	stored as their username.
	"""
	var req := CookieHTTPRequest.new()
	req.request_completed.connect(_on_get_username)
	req.cookie_request(
		# the username is set based on the URL
		api_url + "/user",
		# no special headers are needed
		[""],
		# put the username
		HTTPClient.Method.METHOD_GET
	)


func _on_get_username(result, response_code, headers, body):
	"""
	Performs the updating of the username value.
	"""
	var json = JSON.parse_string(body.get_string_from_utf8())
	# update the global username value
	username = json["username"]
