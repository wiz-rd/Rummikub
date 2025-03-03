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
var user_in_game: bool = false


func create_game() -> void:
	"""
	Sends a request to the server to create a game.
	"""
	var req = CookieHTTPRequest.new()
	add_child(req)

	var full_url = API_URL + "/game"

	req.request_completed.connect(func (_result, response_code, _headers, body):
		if response_code != HTTPClient.RESPONSE_CREATED:
			# TODO: add better error messaging to client
			push_error("The request succeeded but the server failed to create a game.")
			return

		var json = JSON.new()
		json.parse(body.get_string_from_utf8())
		game_data = json.get_data()
	)

	var error = req.cookie_request(
		# the username is set based on the URL
		full_url,
		# placeholder headers
		HTTPCookieStore._retrieve_cookies_for_header(SERVER_DOMAIN),
		# put the username
		HTTPClient.Method.METHOD_POST
	)

	if error:
		# TODO: add better notifications to client
		push_error("Error creating game.")


func join_game(game_id: String) -> bool:
	"""
	Requests the server to join a game.
	Returns true if joining the game was a success.
	"""
	var req = CookieHTTPRequest.new()
	add_child(req)

	var full_url: String = API_URL + "/game/" + game_id + "/join"

	# using an anonymous function here so I can modify a variable
	# without having to use globals
	req.request_completed.connect(func (_result, response_code, _headers, _body):
		if response_code != HTTPClient.RESPONSE_CREATED:
			# TODO: Let client know
			push_error("The join game request succeeded but the server rejected it.")
			Globals.user_in_game = false
			# nothing else is needed to be done. The user should join the game.
		Globals.user_in_game = true
	)

	var error = req.cookie_request(
		full_url,
		HTTPCookieStore._retrieve_cookies_for_header(SERVER_DOMAIN),
		HTTPClient.METHOD_POST
	)

	if error:
		# TODO: better user notification needed
		push_error("Error joining game.")
		Globals.user_in_game = false

	return Globals.user_in_game
