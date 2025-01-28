export interface Appointment {
  id: number;
  patientId: number;
  patientName: string;
  
  date: string;
  time: string;
  details: string;
  status: string;
}
