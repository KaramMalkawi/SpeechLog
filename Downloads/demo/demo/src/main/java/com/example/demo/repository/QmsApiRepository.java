package com.example.demo.repository;

import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import com.example.demo.model.QmsApi;

@Repository
public interface QmsApiRepository extends JpaRepository<QmsApi, Long> {
	Optional<QmsApi> findByTicketNumber(String ticketNumber);
}
