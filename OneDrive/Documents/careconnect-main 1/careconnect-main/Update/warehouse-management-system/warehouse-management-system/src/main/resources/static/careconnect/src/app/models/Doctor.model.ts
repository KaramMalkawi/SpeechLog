export interface Doctor {
  userId: number;
  firstName: string;
  lastName: string;
  description?: string; // Optional field
  userType: string;
  department?: {
    departmentId: number;
    name: string;
  };
}
