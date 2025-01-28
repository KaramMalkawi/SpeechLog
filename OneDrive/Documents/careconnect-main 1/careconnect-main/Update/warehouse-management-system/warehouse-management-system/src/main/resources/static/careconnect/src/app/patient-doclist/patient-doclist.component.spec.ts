import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PatientDoclistComponent } from './patient-doclist.component';

describe('PatientDoclistComponent', () => {
  let component: PatientDoclistComponent;
  let fixture: ComponentFixture<PatientDoclistComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PatientDoclistComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(PatientDoclistComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
