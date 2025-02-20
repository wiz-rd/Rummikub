extends Node

var http_event_source: HTTPEventSource
var GAME_ID: String
var URL: String

func _start_event_listening(game_id: String, url: String, after_url: String):
	http_event_source = HTTPEventSource.new()
	GAME_ID = game_id
	URL = url + game_id + after_url
	http_event_source.connect_to_url(URL)
	http_event_source.event.connect(_on_event)


func _ready() -> void:
	# this should NOT be called on _ready()
	# and instead should wait until user joins a game.
	# just putting it here for now.
	# NOTE: delete this AND add a way to dynamically call this
	_start_event_listening("3e7af25dc3c8466398874f8f7bd1f4bf", "http://127.0.0.1:8000/api/game/", "/notify")


func _on_event(ev: ServerSentEvent):
	"""
	When an event is received, perform the following.
	"""
	print("-- TYPE --")
	print(ev.type)
	print("-- DATA --")
	print(ev.data)
	print("--\t--\n")


func _process(delta: float) -> void:
	# unfortunately this must be checked every
	# "process" but I don't know of a better
	# way to do this atm
	if http_event_source != null:
		http_event_source.poll()
