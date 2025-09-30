package com.example.demo.service;

import java.lang.reflect.Method;
import java.util.Optional;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import com.example.demo.model.ApiConfig;
import com.example.demo.model.IntegrationLog;
import com.example.demo.model.QmsApi;
import com.example.demo.repository.ApiConfigRepository;
import com.example.demo.repository.IntegrationLogRepository;
import com.example.demo.repository.QmsApiRepository;

@Service
public class ExternalApiService {

	private static final Logger logger = LoggerFactory.getLogger(ExternalApiService.class);

	private final QmsApiRepository qmsApiRepository;
	private final IntegrationLogRepository logRepository;
	private final ApiConfigRepository apiConfigRepository;
	private final RestTemplate restTemplate;

	public ExternalApiService(QmsApiRepository qmsApiRepository, IntegrationLogRepository logRepository,
			ApiConfigRepository apiConfigRepository, RestTemplate restTemplate) {
		this.qmsApiRepository = qmsApiRepository;
		this.logRepository = logRepository;
		this.apiConfigRepository = apiConfigRepository;
		this.restTemplate = restTemplate;
	}

	public String triggerEvent(String ticketNumber, String eventType) {
		Optional<QmsApi> qmsApiOptional = qmsApiRepository.findByTicketNumber(ticketNumber);
		if (qmsApiOptional.isEmpty()) {
			return "Ticket not found!";
		}
		QmsApi record = qmsApiOptional.get();
		String normalizedEventType = eventType.toUpperCase();

		Optional<ApiConfig> configOptional = apiConfigRepository.findByEventType(normalizedEventType);
		if (configOptional.isEmpty()) {
			return "API configuration not found for event type: " + eventType;
		}
		ApiConfig config = configOptional.get();

		String url = config.getApiUrl();
		String template = config.getJsonTemplate();
		String httpMethod = config.getHttpMethod();

		String payload = "";
		int statusCode = 0;
		String responseBody = null;
		String errorMessage = null;

		try {
			payload = populateJsonTemplate(template, record);

			logger.info("External API Call Details:");
			logger.info("  URL: {}", url);
			logger.info("  Method: {}", httpMethod);
			logger.info("  Payload:\n{}", payload);

			HttpHeaders headers = new HttpHeaders();
			headers.setContentType(MediaType.APPLICATION_JSON);
			HttpEntity<String> entity = new HttpEntity<>(payload, headers);

			ResponseEntity<String> response = restTemplate.exchange(url, HttpMethod.valueOf(httpMethod.toUpperCase()),
					entity, String.class);

			statusCode = response.getStatusCode().value();
			responseBody = response.getBody();

			logger.info("External API Response Code: {}", statusCode);
			logger.info("External API Response Body: {}", responseBody);

		} catch (Exception e) {
			logger.error("Error during external API call to {}: {}", url, e.getMessage());
			errorMessage = e.getMessage();
		}

		IntegrationLog log = new IntegrationLog();
		log.setQmsApiRecord(record);
		log.setEventType(eventType);
		log.setRequestPayload(payload);
		log.setResponseCode(statusCode);
		log.setResponseBody(responseBody);
		log.setErrorMessage(errorMessage);
		logRepository.save(log);

		return (errorMessage == null)
				? "Event " + eventType + " triggered successfully to " + url + ". Response Code: " + statusCode
				: "Failed to trigger event " + eventType + ": " + errorMessage;
	}

	private String populateJsonTemplate(String template, QmsApi record) {
		String populatedJson = template;

		String[] fields = { "ticketNumber", "agentId", "agentName", "shopName", "terminalNumber", "userdata01",
				"userdata02", "userdata03", "userdata04", "userdata05", "userdata06", "userdata07", "userdata08",
				"userdata09", "userdata10" };

		for (String field : fields) {
			try {
				String getterName = "get" + field.substring(0, 1).toUpperCase() + field.substring(1);

				Method getter = QmsApi.class.getMethod(getterName);
				Object value = getter.invoke(record);

				String replacement = (value != null) ? value.toString() : "";

				populatedJson = populatedJson.replace("{{" + field + "}}", replacement);

				if (field.equals("agentName")) {
					populatedJson = populatedJson.replace("{{agentUserName}}", replacement);
				}

			} catch (Exception e) {
				logger.warn("Reflection error for field {}: {}", field, e.getMessage());
			}
		}
		return populatedJson;
	}
}
