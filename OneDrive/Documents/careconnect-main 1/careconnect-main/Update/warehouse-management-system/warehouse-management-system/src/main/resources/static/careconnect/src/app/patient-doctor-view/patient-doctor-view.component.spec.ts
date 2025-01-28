import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PatientDoctorViewComponent } from './patient-doctor-view.component';

describe('PatientDoctorViewComponent', () => {
  let component: PatientDoctorViewComponent;
  let fixture: ComponentFixture<PatientDoctorViewComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PatientDoctorViewComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(PatientDoctorViewComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
