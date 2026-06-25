import XCTest
@testable import HabitTracker

final class SmokeTest: XCTestCase {
    func testAppEntryPointExists() {
        // Forces the test target to link against the HabitTracker module.
        // If the app target fails to compile, this test fails to build.
        _ = HabitTrackerApp.self
    }

    func testRootViewInstantiates() {
        // SwiftUI views are value types; constructing one verifies the
        // module surface is intact without launching the app.
        _ = RootView()
    }
}
