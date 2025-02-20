extends Node

var http_event_source: HTTPEventSource

func _ready() -> void:
	http_event_source = HTTPEventSource.new()
	var game_id = "3e7af25dc3c8466398874f8f7bd1f4bf"
	var url = "http://127.0.0.1:8000/api/game/" + game_id + "/notify"
	print(url)
	http_event_source.connect_to_url(url)
	http_event_source.event.connect(func(ev: ServerSentEvent):
		print("-- TYPE --")
		print(ev.type)
		print("-- DATA --")
		print(ev.data)
		print("--      --\n")
	)


func _process(delta: float) -> void:
	http_event_source.poll()
