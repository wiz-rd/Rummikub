extends Node

"""
A script that holds some global values and functions.
"""

const MENU_SCENE = "res://scenes/main_menu.tscn"
const LOGIN_SCENE = "res://scenes/create_session.tscn"
const TABLE_SCENE = "res://scenes/table.tscn"
const ATTRIBUTES_SCENE = "res://scenes/attributions.tscn"
const GAME_MANAGEMENT_SCENE = "res://scenes/create_game.tscn"

const SERVER_DOMAIN = "http://127.0.0.1"
const API_STRING = "/api"
# TODO CRITICAL: remove this once an actual hostname/server is used
const PORT = "8000"
# TODO CRITICAL: see above
const API_URL = SERVER_DOMAIN + ":" + PORT + API_STRING

# to be used to store the entire game and information about it
# so it can be acessed from any scene
var game_data: Dictionary


func create_game() -> void:
	"""
	Sends a request to the server to create a game.
	"""
	var req = CookieHTTPRequest.new()
	add_child(req)

	var full_url = Globals.API_URL + "/game"

	req.request_completed.connect(_on_create_game)
	var error = req.cookie_request(
		# the username is set based on the URL
		full_url,
		# no special headers are needed
		HTTPCookieStore._retrieve_cookies_for_header(SERVER_DOMAIN),
		# put the username
		HTTPClient.Method.METHOD_POST
	)

	if error:
		# TODO: add better notifications to client
		push_error("Error creating game.")


func _on_create_game(_result, response_code, _headers, body) -> void:
	if response_code != HTTPClient.RESPONSE_CREATED:
		# TODO: add better error messaging to client
		push_error("The request succeeded but the server failed to create a game.")
		return

	var json = JSON.new()
	json.parse(body.get_string_from_utf8())
	game_data = json.get_data()
