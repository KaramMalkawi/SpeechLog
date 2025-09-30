package com.example.demo.model;

import java.time.LocalDateTime;
import java.util.List;

import jakarta.persistence.CascadeType;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.OneToMany;
import jakarta.persistence.Table;

@Entity
@Table(name = "qmsapi")
public class QmsApi {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	@Column(name = "id")
	private Long id;

	@Column(name = "shop_name")
	private String shopName;

	@Column(name = "terminal_number")
	private String terminalNumber;

	@Column(name = "agent_name")
	private String agentName;

	@Column(name = "agent_id")
	private String agentId;

	@Column(name = "ticket_number", unique = true, nullable = false)
	private String ticketNumber;

	@Column(name = "status")
	private String status;

	@Column(name = "timestamp")
	private LocalDateTime timestamp;

	@Column(name = "userdata_01")
	private String userdata01;

	@Column(name = "userdata_02")
	private String userdata02;

	@Column(name = "userdata_03")
	private String userdata03;

	@Column(name = "userdata_04")
	private String userdata04;

	@Column(name = "userdata_05")
	private String userdata05;

	@Column(name = "userdata_06")
	private String userdata06;

	@Column(name = "userdata_07")
	private String userdata07;

	@Column(name = "userdata_08")
	private String userdata08;

	@Column(name = "userdata_09")
	private String userdata09;

	@Column(name = "userdata_10")
	private String userdata10;

	@OneToMany(mappedBy = "qmsApiRecord", cascade = CascadeType.ALL, orphanRemoval = true)
	private List<IntegrationLog> integrationLogs;

	public QmsApi() {

	}

	public QmsApi(Long id, String shopName, String terminalNumber, String agentName, String agentId,
			String ticketNumber, String status, LocalDateTime timestamp, String userdata01, String userdata02,
			String userdata03, String userdata04, String userdata05, String userdata06, String userdata07,
			String userdata08, String userdata09, String userdata10, List<IntegrationLog> integrationLogs) {
		this.id = id;
		this.shopName = shopName;
		this.terminalNumber = terminalNumber;
		this.agentName = agentName;
		this.agentId = agentId;
		this.ticketNumber = ticketNumber;
		this.status = status;
		this.timestamp = timestamp;
		this.userdata01 = userdata01;
		this.userdata02 = userdata02;
		this.userdata03 = userdata03;
		this.userdata04 = userdata04;
		this.userdata05 = userdata05;
		this.userdata06 = userdata06;
		this.userdata07 = userdata07;
		this.userdata08 = userdata08;
		this.userdata09 = userdata09;
		this.userdata10 = userdata10;
		this.integrationLogs = integrationLogs;
	}

	public Long getId() {
		return id;
	}

	public void setId(Long id) {
		this.id = id;
	}

	public String getShopName() {
		return shopName;
	}

	public void setShopName(String shopName) {
		this.shopName = shopName;
	}

	public String getTerminalNumber() {
		return terminalNumber;
	}

	public void setTerminalNumber(String terminalNumber) {
		this.terminalNumber = terminalNumber;
	}

	public String getAgentName() {
		return agentName;
	}

	public void setAgentName(String agentName) {
		this.agentName = agentName;
	}

	public String getAgentId() {
		return agentId;
	}

	public void setAgentId(String agentId) {
		this.agentId = agentId;
	}

	public String getTicketNumber() {
		return ticketNumber;
	}

	public void setTicketNumber(String ticketNumber) {
		this.ticketNumber = ticketNumber;
	}

	public String getStatus() {
		return status;
	}

	public void setStatus(String status) {
		this.status = status;
	}

	public LocalDateTime getTimestamp() {
		return timestamp;
	}

	public void setTimestamp(LocalDateTime timestamp) {
		this.timestamp = timestamp;
	}

	public String getUserdata01() {
		return userdata01;
	}

	public void setUserdata01(String userdata01) {
		this.userdata01 = userdata01;
	}

	public String getUserdata02() {
		return userdata02;
	}

	public void setUserdata02(String userdata02) {
		this.userdata02 = userdata02;
	}

	public String getUserdata03() {
		return userdata03;
	}

	public void setUserdata03(String userdata03) {
		this.userdata03 = userdata03;
	}

	public String getUserdata04() {
		return userdata04;
	}

	public void setUserdata04(String userdata04) {
		this.userdata04 = userdata04;
	}

	public String getUserdata05() {
		return userdata05;
	}

	public void setUserdata05(String userdata05) {
		this.userdata05 = userdata05;
	}

	public String getUserdata06() {
		return userdata06;
	}

	public void setUserdata06(String userdata06) {
		this.userdata06 = userdata06;
	}

	public String getUserdata07() {
		return userdata07;
	}

	public void setUserdata07(String userdata07) {
		this.userdata07 = userdata07;
	}

	public String getUserdata08() {
		return userdata08;
	}

	public void setUserdata08(String userdata08) {
		this.userdata08 = userdata08;
	}

	public String getUserdata09() {
		return userdata09;
	}

	public void setUserdata09(String userdata09) {
		this.userdata09 = userdata09;
	}

	public String getUserdata10() {
		return userdata10;
	}

	public void setUserdata10(String userdata10) {
		this.userdata10 = userdata10;
	}

	public List<IntegrationLog> getIntegrationLogs() {
		return integrationLogs;
	}

	public void setIntegrationLogs(List<IntegrationLog> integrationLogs) {
		this.integrationLogs = integrationLogs;
	}

}
