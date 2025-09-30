package com.example.demo.model;

import java.time.LocalDateTime;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.Lob;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;

@Entity
@Table(name = "integration_log")
public class IntegrationLog {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	@Column(name = "log_id")
	private Long logId;

	@ManyToOne(fetch = FetchType.LAZY)
	@JoinColumn(name = "qmsapi_record_id", nullable = false)
	private QmsApi qmsApiRecord;

	@Column(name = "event_type")
	private String eventType;

	@Lob
	@Column(name = "request_payload", columnDefinition = "TEXT")
	private String requestPayload;

	@Column(name = "response_code")
	private Integer responseCode;

	@Lob
	@Column(name = "response_body", columnDefinition = "TEXT")
	private String responseBody;

	@Column(name = "log_timestamp")
	private LocalDateTime logTimestamp = LocalDateTime.now();

	@Column(name = "error_message")
	private String errorMessage;

	public IntegrationLog() {

	}

	public IntegrationLog(Long logId, QmsApi qmsApiRecord, String eventType, String requestPayload,
			Integer responseCode, String responseBody, LocalDateTime logTimestamp, String errorMessage) {
		this.logId = logId;
		this.qmsApiRecord = qmsApiRecord; // Changed name
		this.eventType = eventType;
		this.requestPayload = requestPayload;
		this.responseCode = responseCode;
		this.responseBody = responseBody;
		this.logTimestamp = logTimestamp;
		this.errorMessage = errorMessage;
	}

	public Long getLogId() {
		return logId;
	}

	public void setLogId(Long logId) {
		this.logId = logId;
	}

	public QmsApi getQmsApiRecord() {
		return qmsApiRecord;
	}

	public void setQmsApiRecord(QmsApi qmsApiRecord) {
		this.qmsApiRecord = qmsApiRecord;
	}

	public String getEventType() {
		return eventType;
	}

	public void setEventType(String eventType) {
		this.eventType = eventType;
	}

	public String getRequestPayload() {
		return requestPayload;
	}

	public void setRequestPayload(String requestPayload) {
		this.requestPayload = requestPayload;
	}

	public Integer getResponseCode() {
		return responseCode;
	}

	public void setResponseCode(Integer responseCode) {
		this.responseCode = responseCode;
	}

	public String getResponseBody() {
		return responseBody;
	}

	public void setResponseBody(String responseBody) {
		this.responseBody = responseBody;
	}

	public LocalDateTime getLogTimestamp() {
		return logTimestamp;
	}

	public void setLogTimestamp(LocalDateTime logTimestamp) {
		this.logTimestamp = logTimestamp;
	}

	public String getErrorMessage() {
		return errorMessage;
	}

	public void setErrorMessage(String errorMessage) {
		this.errorMessage = errorMessage;
	}

}
