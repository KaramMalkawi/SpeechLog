import { Appointment } from '../models/Appointment.model';
import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common'; // Import CommonModule

@Component({
  selector: 'app-doctor-home',
  standalone: true, // Add this if using standalone components
  imports: [CommonModule], // Add CommonModule here
  templateUrl: './doctor-home.component.html',
  styleUrl: './doctor-home.component.scss',
})

export class DoctorHomeComponent implements OnInit {
  appointments: Appointment[] = [];
  doctorId: number | null = null;
  token: string | null = null;

  constructor(private router: Router) {
    this.token = localStorage.getItem('token');
    if (!this.token) {
      this.router.navigate(['/auth/login']);
    }
    this.doctorId = Number(localStorage.getItem('userId'));
  }

  ngOnInit(): void {
    this.fetchDoctorAppointments();
  }

  fetchDoctorAppointments() {
    fetch(`http://localhost:8080/appointments/user/${this.doctorId}`, {
      headers: {
        Authorization: `Bearer ${this.token}`,
        'Content-Type': 'application/json',
      },
    })
      .then((response) => {
        if (!response.ok) throw new Error('Failed to fetch appointments');
        return response.json();
      })
      .then((data) => {
        this.appointments = data;
      })
      .catch((error) => console.error('Error:', error));
  }

  navigateTo(route: string) {
    this.router.navigate([`/${route}`]);
  }

  addReport(appointmentId: number) {
    this.router.navigate(['/add-report', appointmentId]);
  }
}