extends Node

var http_event_source: HTTPEventSource
var board: Dictionary
var game_id: String

# board should be as follows:
# "game": game,
# "hand": hand,
# "player_data": player_hands,
## (a dictionary
## of username : len(hand))
# "pool_size": pool_size,


func _ready() -> void:
	# connecting to the server to be notified of changes
	game_id = Globals.game_data["id"]

	if game_id == "" or game_id == null:
		push_error("The user is at a table but not in a game.")
		# CRITICAL Notify user of this
		return

	var notify_url = Globals.API_URL + "/game/" + game_id + "/notify"
	http_event_source = HTTPEventSource.new()
	http_event_source.connect_to_url(notify_url)
	http_event_source.event.connect(func(ev: ServerSentEvent):
		# when an event is received from the server,
		# update the board.
		print("-- TYPE --")
		print(ev.type)
		print("-- DATA --")
		print(ev.data)
		print("--      --\n")
	)


func _process(delta: float) -> void:
	http_event_source.poll()


func update_board_dict():
	"""
	Updates the whole dictionary.
	"""
	var req = CookieHTTPRequest.new()
	add_child(req)

	if game_id == null or game_id == "":
		# CRITICAL Notify user of this
		push_error("The user is at the table scene but is not in a game.")
		return

	var full_url = Globals.API_URL + "/game/" + game_id + "/board"

	var session_id = HTTPCookieStore.get_cookie_header_for_request(Globals.SERVER_DOMAIN)
	if session_id == null:
		session_id = HTTPCookieStore._retrieve_cookies_for_header(Globals.SERVER_DOMAIN)

	#
	# Anonymous function to get board data
	#
	req.request_completed.connect(func(_result, response_code, _headers, body):
		"""
		Updates the board dictionary.
		"""
		if response_code != HTTPClient.RESPONSE_OK:
			push_error("There was an error obtaining the board.")
			# CRITICAL TODO: Notify the user if this fails
		else:
			var json = JSON.new()
			json.parse(body.get_string_from_utf8())
			board = json.get_data()
		)
	#
	# End of board-data anonymous function
	#

	var error = req.cookie_request(
		# the URL
		full_url,
		# the cookies, because I have to pass an argument here
		session_id,
		# get the board info
		HTTPClient.Method.METHOD_GET
	)

	if error:
		# CRITICAL notify client of this AND/OR re-request board
		push_error("Error in getting board data from url '" + full_url + "'.")
