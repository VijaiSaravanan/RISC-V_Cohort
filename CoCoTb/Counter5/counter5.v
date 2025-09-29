module counter5 (
    input  wire clk,
    input  wire rst,  // synchronous reset
    input  wire en,   // enable
    output reg [4:0] count
);

always @(posedge clk) begin
    if (rst)
        count <= 5'd0;
    else if (en) begin
        if (count == 5'd31)
            count <= 5'd0;  // wrap around when enabled
        else
            count <= count + 1;
    end
    else
        count <= count;  // hold value when enable=0
end

endmodule
