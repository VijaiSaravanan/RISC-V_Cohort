// Sum N inputs each W bits wide. Behavioral simple accumulation.
module wallace_tree #(parameter IN_N = 8, parameter W = 32) (
    input  wire [IN_N*W-1:0] in_vec_flat,
    output reg  signed [W+8:0] out
);
    integer i;
    reg signed [W-1:0] tmp;
    always @(*) begin
        out = 0;
        for (i=0;i<IN_N;i=i+1) begin
            tmp = in_vec_flat[i*W +: W];
            out = out + tmp;
        end
    end
endmodule
