import { Report } from './../models/report.model';
import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';

@Component({
  selector: 'app-patient-report',
  imports: [CommonModule],
  templateUrl: './patient-report.component.html',
  styleUrl: './patient-report.component.scss'
})

export class PatientReportComponent implements OnInit {
  reports: Report[] = [];
  token: string | null = null;
 
  constructor(private router: Router) {
    this.token = localStorage.getItem('token');
    if (!this.token) {
      this.redirectToLogin();
    }
  }
 
  ngOnInit(): void {
    this.fetchReports();
  }
 
  fetchReports(): void {
    fetch('http://localhost:8080/reports/all', {
      headers: {
        'Authorization': `Bearer ${this.token}`
      }
    })
      .then(response => {
        if (!response.ok) {
          throw new Error('Failed to fetch reports');
        }
        return response.json();
      })
      .then(data => {
        this.reports = data.map((report: any) => ({
          doctor: {
            firstName: report.doctor.firstName,
            lastName: report.doctor.lastName,
          },
          diagnosis: report.diagnosis,
          description: report.description,
          createdAt: report.createdAt,
        }));
      })
      .catch(error => {
        console.error('Error fetching reports:', error);
      });
  }
   
  navigateTo(route: string): void {
    this.router.navigate([`/${route}`]);
  }
 
  redirectToLogin(): void {
    this.router.navigate(['/login']);
  }
}