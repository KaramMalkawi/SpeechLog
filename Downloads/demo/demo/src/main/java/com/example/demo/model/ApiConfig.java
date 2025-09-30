package com.example.demo.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "api_config")
public class ApiConfig {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	@Column(name = "config_id")
	private Long configId;

	@Column(name = "event_type", unique = true, nullable = false)
	private String eventType;

	@Column(name = "api_url", length = 512, nullable = false)
	private String apiUrl;

	@Column(name = "http_method")
	private String httpMethod;

	@Column(name = "json_template", columnDefinition = "TEXT")
	private String jsonTemplate;

	public ApiConfig() {
	}

	public ApiConfig(Long configId, String eventType, String apiUrl, String httpMethod, String jsonTemplate) {
		this.configId = configId;
		this.eventType = eventType;
		this.apiUrl = apiUrl;
		this.httpMethod = httpMethod;
		this.jsonTemplate = jsonTemplate;
	}

	public Long getConfigId() {
		return configId;
	}

	public void setConfigId(Long configId) {
		this.configId = configId;
	}

	public String getEventType() {
		return eventType;
	}

	public void setEventType(String eventType) {
		this.eventType = eventType;
	}

	public String getApiUrl() {
		return apiUrl;
	}

	public void setApiUrl(String apiUrl) {
		this.apiUrl = apiUrl;
	}

	public String getHttpMethod() {
		return httpMethod;
	}

	public void setHttpMethod(String httpMethod) {
		this.httpMethod = httpMethod;
	}

	public String getJsonTemplate() {
		return jsonTemplate;
	}

	public void setJsonTemplate(String jsonTemplate) {
		this.jsonTemplate = jsonTemplate;
	}

}
