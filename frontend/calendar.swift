import SwiftUI

struct ContentView: View {
    let year: Int
    let month: Int
    
    let daysInMonth: Int
    let firstWeekday: Int
    let columns = Array(repeating: GridItem(.flexible()), count: 7)
    
    init(year: Int = 2026, month: Int = 1) {
        self.year = year
        self.month = month
        
        let calendar = Calendar.current
        var components = DateComponents()
        components.year = year
        components.month = month
        components.day = 1
        let firstDayOfMonth = calendar.date(from: components)!
        
        self.daysInMonth = calendar.range(of: .day, in: .month, for: firstDayOfMonth)!.count
        self.firstWeekday = calendar.component(.weekday, from: firstDayOfMonth) - 1
    }

    var body: some View {
        VStack {
            Text("\(String(year))년 \(month)월")
                .font(.largeTitle)
                .fontWeight(.bold)
                .padding()
            
            HStack {
                ForEach(["일", "월", "화", "수", "목", "금", "토"], id: \.self) { day in
                    Text(day)
                        .fontWeight(.semibold)
                        .frame(maxWidth: .infinity)
                        .foregroundColor(day == "일" ? .red : .primary)
                }
            }
            
            LazyVGrid(columns: columns, spacing: 20) {
                ForEach(0..<firstWeekday, id: \.self) { _ in
                    Text("")
                        .frame(maxWidth: .infinity)
                }
                
                ForEach(1...daysInMonth, id: \.self) { day in
                    Text("\(day)")
                        .frame(maxWidth: .infinity)
                        .foregroundColor(day % 7 == 0 ? .blue : (day % 7 == 1 ? .red : .primary))
                        .padding(8)
                        .background(
                            (day == 13 && month == 1 && year == 2026) ? Circle().fill(Color.blue.opacity(0.3)) : nil
                        )
                }
            }
            .padding()
        }
    }
}

// 미리보기 설정 부분도 이름을 맞춰줍니다.
struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}
