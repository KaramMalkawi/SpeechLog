package com.example.demo.controller;

import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.example.demo.service.ExternalApiService;

@RestController
@RequestMapping("/events")
public class EventController {

	private final ExternalApiService externalApiService;

	public EventController(ExternalApiService externalApiService) {
		this.externalApiService = externalApiService;
	}

	@PostMapping("/{ticketNumber}/start")
	public String triggerStart(@PathVariable String ticketNumber) {
		return externalApiService.triggerEvent(ticketNumber, "start");
	}

	@PostMapping("/{ticketNumber}/stop")
	public String triggerStop(@PathVariable String ticketNumber) {
		return externalApiService.triggerEvent(ticketNumber, "stop");
	}
}
