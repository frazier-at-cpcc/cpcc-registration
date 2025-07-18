#!/usr/bin/env python3
"""
Test script to verify instructor extraction logic works with sample data.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from services.section_details import SectionDetailsService
from services.session_manager import CPCCSessionManager

def test_instructor_extraction():
    """Test instructor extraction with sample data that contains instructor information."""
    
    # Sample data based on the user's provided API response
    sample_response = {
        "SectionsRetrieved": {
            "TermsAndSections": [
                {
                    "Term": {
                        "Code": "2025FA",
                        "Description": "Fall 2025"
                    },
                    "Sections": [
                        {
                            "Section": {
                                "Id": "344349",
                                "CourseId": "S26503",
                                "SectionNameDisplay": "CTI-110-H103",
                                "SectionTitleDisplay": "IT Foundations",
                                "Available": 0,
                                "Capacity": 24,
                                "Enrolled": 24,
                                "Waitlisted": 0,
                                "StartDateDisplay": "8/18/2025",
                                "EndDateDisplay": "10/10/2025",
                                "LocationDisplay": "Central Campus / CPCC",
                                "MinimumCredits": 3.0,
                                "FormattedMeetingTimes": [
                                    {
                                        "DaysOfWeekDisplay": "T/Th",
                                        "StartTimeDisplay": "12:30 PM",
                                        "EndTimeDisplay": "1:50 PM",
                                        "InstructionalMethodDisplay": "Classroom Hours",
                                        "BuildingDisplay": "Levine Technology Bldg",
                                        "RoomDisplay": "5134",
                                        "DatesDisplay": "8/18/2025 - 10/10/2025",
                                        "IsOnline": False
                                    }
                                ],
                                "Meetings": [],
                                "PrimarySectionMeetings": []
                            },
                            "FacultyDisplay": "Saxena, Aastha X.",
                            "InstructorDetails": [
                                {
                                    "FacultyId": "4363073",
                                    "FacultyName": "Saxena, Aastha X.",
                                    "AdvisorType": None,
                                    "InstructorMethod": "Classroom Hours, Online Lab",
                                    "AdvisorTypeRank": None
                                }
                            ],
                            "DisplayOfficeHours": False,
                            "AvailabilityDisplay": "0 / 24 / 0",
                            "ShowCatalogListingSeatCountFormatIfWaitlisted": False
                        },
                        {
                            "Section": {
                                "Id": "334727",
                                "CourseId": "S23205",
                                "SectionNameDisplay": "CTI-140-N880",
                                "SectionTitleDisplay": "Virtualization Concepts",
                                "Available": 0,
                                "Capacity": 18,
                                "Enrolled": 21,
                                "Waitlisted": 3,
                                "StartDateDisplay": "8/18/2025",
                                "EndDateDisplay": "10/10/2025",
                                "LocationDisplay": "Central Campus / CPCC",
                                "MinimumCredits": 3.0,
                                "FormattedMeetingTimes": [
                                    {
                                        "DaysOfWeekDisplay": "M/T/W/Th/F/Sa/Su",
                                        "StartTimeDisplay": "",
                                        "EndTimeDisplay": "",
                                        "InstructionalMethodDisplay": "Online Class",
                                        "BuildingDisplay": "ON",
                                        "RoomDisplay": "LINE",
                                        "DatesDisplay": "8/18/2025 - 10/10/2025",
                                        "IsOnline": True
                                    }
                                ],
                                "Meetings": [],
                                "PrimarySectionMeetings": []
                            },
                            "FacultyDisplay": "Renner, Chuck",
                            "InstructorDetails": [
                                {
                                    "FacultyId": "1234567",
                                    "FacultyName": "Renner, Chuck",
                                    "AdvisorType": None,
                                    "InstructorMethod": "Online Class",
                                    "AdvisorTypeRank": None
                                }
                            ],
                            "DisplayOfficeHours": False,
                            "AvailabilityDisplay": "0 / 18 / 3",
                            "ShowCatalogListingSeatCountFormatIfWaitlisted": False
                        },
                        {
                            "Section": {
                                "Id": "344350",
                                "CourseId": "S26503",
                                "SectionNameDisplay": "CTI-110-N861",
                                "SectionTitleDisplay": "IT Foundations",
                                "Available": 0,
                                "Capacity": 27,
                                "Enrolled": 27,
                                "Waitlisted": 2,
                                "StartDateDisplay": "8/18/2025",
                                "EndDateDisplay": "10/10/2025",
                                "LocationDisplay": "Central Campus / CPCC",
                                "MinimumCredits": 3.0,
                                "FormattedMeetingTimes": [
                                    {
                                        "DaysOfWeekDisplay": "M/T/W/Th/F/Sa/Su",
                                        "StartTimeDisplay": "",
                                        "EndTimeDisplay": "",
                                        "InstructionalMethodDisplay": "Online Class",
                                        "BuildingDisplay": "ON",
                                        "RoomDisplay": "LINE",
                                        "DatesDisplay": "8/18/2025 - 10/10/2025",
                                        "IsOnline": True
                                    }
                                ],
                                "Meetings": [],
                                "PrimarySectionMeetings": []
                            },
                            "FacultyDisplay": "Moore, Joel",
                            "InstructorDetails": [
                                {
                                    "FacultyId": "0081811",
                                    "FacultyName": "Moore, Joel",
                                    "AdvisorType": None,
                                    "InstructorMethod": "Online Class, Online Lab",
                                    "AdvisorTypeRank": None
                                }
                            ],
                            "DisplayOfficeHours": False,
                            "AvailabilityDisplay": "0 / 27 / 2",
                            "ShowCatalogListingSeatCountFormatIfWaitlisted": False
                        },
                        {
                            "Section": {
                                "Id": "344354",
                                "CourseId": "S26503",
                                "SectionNameDisplay": "CTI-110-N864",
                                "SectionTitleDisplay": "IT Foundations",
                                "Available": 16,
                                "Capacity": 27,
                                "Enrolled": 11,
                                "Waitlisted": 0,
                                "StartDateDisplay": "10/20/2025",
                                "EndDateDisplay": "12/12/2025",
                                "LocationDisplay": "Central Campus / CPCC",
                                "MinimumCredits": 3.0,
                                "FormattedMeetingTimes": [
                                    {
                                        "DaysOfWeekDisplay": "M/T/W/Th/F/Sa/Su",
                                        "StartTimeDisplay": "",
                                        "EndTimeDisplay": "",
                                        "InstructionalMethodDisplay": "Online Class",
                                        "BuildingDisplay": "ON",
                                        "RoomDisplay": "LINE",
                                        "DatesDisplay": "10/20/2025 - 12/12/2025",
                                        "IsOnline": True
                                    }
                                ],
                                "Meetings": [],
                                "PrimarySectionMeetings": []
                            },
                            "FacultyDisplay": "",
                            "InstructorDetails": [],
                            "DisplayOfficeHours": False,
                            "AvailabilityDisplay": "16 / 27 / 0",
                            "ShowCatalogListingSeatCountFormatIfWaitlisted": False
                        }
                    ]
                }
            ]
        }
    }
    
    # Create a mock session manager
    class MockSessionManager:
        pass
    
    # Create service instance
    service = SectionDetailsService(MockSessionManager())
    
    # Test the parsing
    print("Testing instructor extraction with sample data...")
    sections = service._parse_sections_response(sample_response)
    
    print(f"\nParsed {len(sections)} sections:")
    
    for section in sections:
        print(f"\nSection: {section.number}")
        print(f"  Title: {section.title}")
        print(f"  Instructors: {section.instructor_names}")
        print(f"  Available: {section.available}/{section.capacity}")
    
    # Verify expected results
    expected_results = {
        "CTI-110-H103": ["Saxena, Aastha X."],
        "CTI-140-N880": ["Renner, Chuck"],
        "CTI-110-N861": ["Moore, Joel"],
        "CTI-110-N864": []
    }
    
    print("\n" + "="*50)
    print("VERIFICATION RESULTS:")
    print("="*50)
    
    all_correct = True
    for section in sections:
        expected = expected_results.get(section.number, [])
        actual = section.instructor_names
        
        if actual == expected:
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
            all_correct = False
        
        print(f"{status} {section.number}: Expected {expected}, Got {actual}")
    
    print("\n" + "="*50)
    if all_correct:
        print("🎉 ALL TESTS PASSED! Instructor extraction is working correctly.")
    else:
        print("❌ SOME TESTS FAILED! There are issues with instructor extraction.")
    print("="*50)
    
    return all_correct

if __name__ == "__main__":
    test_instructor_extraction()