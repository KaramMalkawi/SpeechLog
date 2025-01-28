import { Routes } from '@angular/router';
import { LoginComponent } from './login/login.component';
import { SignupPatientComponent } from './signup-patient/signup-patient.component';
import { SignupDoctorComponent } from './signup-doctor/signup-doctor.component';
import { PatientHomeComponent } from './patient-home/patient-home.component';
import { DoctorHomeComponent } from './doctor-home/doctor-home.component';
import { PatientDoclistComponent } from './patient-doclist/patient-doclist.component';
import { PatientReportComponent } from './patient-report/patient-report.component';

export const routes: Routes = [
    { path: '', component: LoginComponent },
    { path: 'signup-patient', component: SignupPatientComponent },
    { path: 'signup-doctor', component: SignupDoctorComponent },
    { path: 'patient-home', component: PatientHomeComponent },
    { path: 'doctor-home', component: DoctorHomeComponent },
    { path: 'patient-doclist', component: PatientDoclistComponent },
    { path: 'patient-report', component: PatientReportComponent }
];
